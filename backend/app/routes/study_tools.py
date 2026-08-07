"""Routes for standalone study tools generated from a module's content: Flash Cards and Quiz Me."""

from flask import Blueprint, abort, jsonify
from flask.wrappers import Response

from app.services.llm_schemas import LLMOutputValidationError
from app.services.module_generation import ModuleNotFoundError
from app.services.study_tools_generation import ModuleNotGeneratedError, generate_flash_cards, generate_quiz_set

study_tools_bp = Blueprint("study_tools", __name__)


@study_tools_bp.post("/api/modules/<module_id>/flash-cards")
def post_flash_cards(module_id: str) -> Response:
    """Generate (or return the already-generated) flash card set for a module.

    Idempotent: a module that already has a saved flash card set returns it
    unchanged - flash cards are never regenerated once created.

    Args:
        module_id: The module's id.

    Returns:
        The module's flash card set.

    Raises:
        404: If no module matches module_id.
        400: If the module has no generated activities yet.
        502: If the model's response couldn't be used.
    """
    try:
        flash_card_set = generate_flash_cards(module_id)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except ModuleNotGeneratedError:
        abort(400, description=f"Module '{module_id}' has no generated content yet")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(flash_card_set.to_dict())


@study_tools_bp.post("/api/modules/<module_id>/quiz-set")
def post_quiz_set(module_id: str) -> Response:
    """Generate (or return the already-generated) Quiz Me quiz for a module.

    Idempotent, same as post_flash_cards().

    Args:
        module_id: The module's id.

    Returns:
        The module's quiz set.

    Raises:
        404: If no module matches module_id.
        400: If the module has no generated activities yet.
        502: If the model's response couldn't be used.
    """
    try:
        quiz_set = generate_quiz_set(module_id)
    except ModuleNotFoundError:
        abort(404, description=f"No module with id '{module_id}'")
    except ModuleNotGeneratedError:
        abort(400, description=f"Module '{module_id}' has no generated content yet")
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")
    return jsonify(quiz_set.to_dict())
