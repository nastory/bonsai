"""Routes for module-level operations: generating a module's activities."""

from flask import Blueprint, abort, jsonify
from flask.wrappers import Response

from app.services.llm_schemas import LLMOutputValidationError
from app.services.module_generation import ModuleNotFoundError, generate_module_activities

modules_bp = Blueprint("modules", __name__)


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
