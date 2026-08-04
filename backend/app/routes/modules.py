"""Routes for module-level operations: generating a module's activities, and
the "Change This Course" mid-course direction-change interview/proposal/approve flow."""

from flask import Blueprint, abort, jsonify, request
from flask.wrappers import Response

from app.services.course_generation import (
    approve_direction_change,
    generate_direction_change_outline,
    start_direction_change,
    submit_direction_change_answer,
    submit_direction_change_feedback,
)
from app.services.llm_schemas import LLMOutputValidationError
from app.services.module_generation import ModuleNotFoundError, generate_module_activities

modules_bp = Blueprint("modules", __name__)


def _direction_interview_step_response(step) -> dict:
    return {"done": step.done, "question": step.question}


@modules_bp.post("/api/modules/<module_id>/generate-activities")
def post_generate_activities(module_id: str) -> Response:
    """Generate (or return already-generated) activities for a module.

    Args:
        module_id: The module's id.

    Returns:
        The serialized parent course, with the module's activities populated.
    """
    try:
        module = generate_module_activities(module_id)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(module.course.to_dict())


@modules_bp.post("/api/modules/<module_id>/direction-interview")
def post_start_direction_change(module_id: str) -> Response:
    """Start the "Change This Course" mid-course check-in interview.

    Body: {"message": "..."}

    Args:
        module_id: The just-completed module's id.

    Returns:
        done=False and the first check-in question.
    """
    message = (request.get_json(force=True) or {}).get("message", "")
    try:
        step = start_direction_change(module_id, message)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(_direction_interview_step_response(step))


@modules_bp.post("/api/modules/<module_id>/direction-interview-messages")
def post_direction_change_answer(module_id: str) -> Response:
    """Submit an answer to the current direction-change check-in question.

    Body: {"answer": "..."}

    Args:
        module_id: The module's id.

    Returns:
        The next question, or done=True once there's enough to propose new modules.
    """
    answer = (request.get_json(force=True) or {}).get("answer", "")
    try:
        step = submit_direction_change_answer(module_id, answer)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(_direction_interview_step_response(step))


@modules_bp.post("/api/modules/<module_id>/direction-outline")
def post_generate_direction_change_outline(module_id: str) -> Response:
    """Propose a new set of modules to replace what's ahead, from the check-in interview so far.

    Nothing is applied yet — see approve_direction_change().

    Args:
        module_id: The module's id.

    Returns:
        The proposed modules.
    """
    try:
        proposal = generate_direction_change_outline(module_id)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(proposal.model_dump())


@modules_bp.post("/api/modules/<module_id>/direction-outline-feedback")
def post_direction_change_feedback(module_id: str) -> Response:
    """Regenerate the proposed modules based on the learner's revision feedback.

    Body: {"feedback": "..."}

    Args:
        module_id: The module's id.

    Returns:
        The revised proposed modules.
    """
    feedback = (request.get_json(force=True) or {}).get("feedback", "")
    try:
        proposal = submit_direction_change_feedback(module_id, feedback)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(proposal.model_dump())


@modules_bp.post("/api/modules/<module_id>/direction-outline-approve")
def post_approve_direction_change(module_id: str) -> Response:
    """Commit the most recently proposed modules, replacing everything ahead of this module.

    Args:
        module_id: The module's id.

    Returns:
        The serialized course, with its remaining modules replaced.
    """
    try:
        course = approve_direction_change(module_id)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}', or no proposal to approve")
    return jsonify(course.to_dict())
