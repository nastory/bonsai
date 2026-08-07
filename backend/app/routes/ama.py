"""Routes for Ask Me Anything: a chat scoped to the learner's own course materials."""

from flask import Blueprint, abort, jsonify, request
from flask.wrappers import Response

from app.services.ama import answer_ama_question
from app.services.llm_schemas import LLMOutputValidationError

ama_bp = Blueprint("ama", __name__)


@ama_bp.post("/api/ama/messages")
def post_ama_message() -> Response:
    """Answer one Ask Me Anything turn.

    No persistence: the client sends its own transcript as `history` each
    time and owns the chat's lifetime (resets on reload).

    Body:
        message: The learner's latest message.
        history: Prior turns, each ``{"role", "content"}``, oldest first.

    Returns:
        {"reply", "courseIds", "citations"}.

    Raises:
        400: If `message` is missing or empty.
        502: If the model's response couldn't be used.
    """
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        abort(400, description="message is required")
    history = body.get("history") or []

    try:
        result = answer_ama_question(message, history)
    except LLMOutputValidationError as e:
        abort(502, description=f"The model's response couldn't be used: {e}")

    return jsonify(
        {
            "reply": result.reply,
            "courseIds": result.course_ids,
            "citations": [c.model_dump() for c in result.citations],
        }
    )
