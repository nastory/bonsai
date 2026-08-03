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
from app.services.document_extraction import DocumentExtractionError
from app.services.llm_schemas import LLMOutputValidationError

course_creation_bp = Blueprint("course_creation", __name__)


def _interview_step_response(step) -> dict:
    return {
        "courseId": step.course.id,
        "done": step.done,
        "question": step.question,
        "sourceMaterials": [s.to_dict() for s in step.course.source_materials],
    }


@course_creation_bp.post("/api/courses")
def create_course() -> tuple[Response, int]:
    """Start a new course from the learner's initial description, optionally with attached documents.

    Multipart form data: `message` (str), `files` (0+ file parts).

    Returns:
        The new course's id, the first interview question, and any attached
        source materials.
    """
    message = request.form.get("message", "")
    files = request.files.getlist("files")
    try:
        step = start_course(message, files)
    except DocumentExtractionError as e:
        return jsonify({"error": str(e)}), 422
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(_interview_step_response(step)), 201


@course_creation_bp.post("/api/courses/<course_id>/interview-messages")
def post_interview_answer(course_id: str) -> Response:
    """Submit an answer to the current interview question, optionally with attached documents.

    Args:
        course_id: The course's id.

    Multipart form data: `answer` (str), `files` (0+ file parts).

    Returns:
        The next interview question, or done=True once there are enough answers.
    """
    answer = request.form.get("answer", "")
    files = request.files.getlist("files")
    try:
        step = submit_interview_answer(course_id, answer, files)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    except DocumentExtractionError as e:
        return jsonify({"error": str(e)}), 422
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
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(course.to_dict())
