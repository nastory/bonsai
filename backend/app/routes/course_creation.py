"""Routes for the course-creation flow: interview -> outline -> approve."""

from flask import Blueprint, abort, jsonify, request
from flask.wrappers import Response

from app.services.course_generation import (
    CourseNotFoundError,
    approve_outline,
    generate_outline,
    start_course,
    submit_interview_answer,
    submit_outline_feedback,
)
from app.services.llm_schemas import LLMOutputValidationError

course_creation_bp = Blueprint("course_creation", __name__)


def _interview_step_response(step) -> dict:
    return {"courseId": step.course.id, "done": step.done, "question": step.question}


@course_creation_bp.post("/api/courses")
def create_course() -> tuple[Response, int]:
    """Start a new course from the learner's initial description.

    Returns:
        The new course's id and the first interview question.
    """
    body = request.get_json(force=True) or {}
    message = body.get("message", "")
    try:
        step = start_course(message)
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(_interview_step_response(step)), 201


@course_creation_bp.post("/api/courses/<course_id>/interview-messages")
def post_interview_answer(course_id: str) -> Response:
    """Submit an answer to the current interview question.

    Args:
        course_id: The course's id.

    Returns:
        The next interview question, or done=True once there are enough answers.
    """
    body = request.get_json(force=True) or {}
    answer = body.get("answer", "")
    try:
        step = submit_interview_answer(course_id, answer)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(_interview_step_response(step))


@course_creation_bp.post("/api/courses/<course_id>/generate-outline")
def post_generate_outline(course_id: str) -> Response:
    """Generate and persist a course outline from the interview so far.

    Args:
        course_id: The course's id.

    Returns:
        The serialized course, now with modules and stage='outline_review'.
    """
    try:
        course = generate_outline(course_id)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(course.to_dict())


@course_creation_bp.post("/api/courses/<course_id>/outline-feedback")
def post_outline_feedback(course_id: str) -> Response:
    """Regenerate the outline based on the learner's requested changes.

    Args:
        course_id: The course's id.

    Returns:
        The serialized course with a freshly regenerated outline.
    """
    body = request.get_json(force=True) or {}
    feedback = body.get("feedback", "")
    try:
        course = submit_outline_feedback(course_id, feedback)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(course.to_dict())


@course_creation_bp.post("/api/courses/<course_id>/approve-outline")
def post_approve_outline(course_id: str) -> Response:
    """Approve the current outline and start the course.

    Args:
        course_id: The course's id.

    Returns:
        The serialized, now-active course.
    """
    try:
        course = approve_outline(course_id)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    return jsonify(course.to_dict())
