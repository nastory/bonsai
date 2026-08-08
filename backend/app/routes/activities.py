"""Routes for mutating individual learning activities.

There's no separate "modules" or "courses" mutation endpoint for this: the
module-completion cascade that used to live only in the frontend now lives
here, so progress survives a refresh.
"""

from datetime import datetime

from flask import Blueprint, abort, jsonify, request
from flask.wrappers import Response

from app.extensions import db
from app.models import Activity, UserSettings
from app.services.activity_feedback import generate_activity_feedback
from app.services.discussion import DiscussionNotAvailableError, generate_discussion_reply
from app.services.llm_schemas import LLMOutputValidationError

activities_bp = Blueprint("activities", __name__)


@activities_bp.post("/api/activities/<activity_id>/complete")
def complete_activity(activity_id: str) -> Response:
    """Mark an activity completed, unlocking the next module once its module is done.

    A module's activities are all generated together and available to the
    learner from the start (see module_generation.py), so there's no
    per-activity unlock cascade: only "has this module finished generating"
    gates access, never completion order within one. Completing a module's
    last activity marks the module completed and unlocks the next module.

    Args:
        activity_id: The activity's id.

    Returns:
        The full serialized course the activity belongs to, reflecting the update.
    """
    activity = db.session.get(Activity, activity_id)
    if activity is None:
        abort(404, description=f"No activity with id '{activity_id}'")

    activity.status = "completed"
    activity.completed_at = datetime.utcnow()

    module = activity.module
    if all(a.status == "completed" for a in module.activities):
        module.status = "completed"

        course = module.course
        next_module = next((m for m in course.modules if m.position == module.position + 1), None)
        if next_module is not None:
            if next_module.status == "locked":
                next_module.status = "in_progress"
        else:
            course.stage = "completed"

    db.session.commit()

    return jsonify(module.course.to_dict())


@activities_bp.post("/api/activities/<activity_id>/feedback")
def generate_feedback(activity_id: str) -> Response:
    """Generate real feedback on a learner's free-text response to an activity.

    Covers essay/project/capstone activities only - the activity's own
    prompt is derived server-side from its stored content, not trusted
    from the client, matching this codebase's general "server derives what
    it can" convention. Quiz/assessment activities reject this: they
    already have real per-question feedback from generation
    (correctAnswerIndex/explanation), checked deterministically on the
    frontend - a reading's optional comprehension check (`checkQuestion`)
    is the same shape and checked the same way, not a free-text response.
    Discussion activities reject this too - they're a real multi-turn
    conversation with their own endpoint instead (see
    post_discussion_message() below).

    Args:
        activity_id: The activity's id.

    Returns:
        {"feedback": str}

    Raises:
        400: If activity_id doesn't take free-text feedback, or the request
            has no non-empty "response".
        404: If no activity matches activity_id.
        502: If the LLM's response doesn't match ActivityFeedbackSchema.
    """
    activity = db.session.get(Activity, activity_id)
    if activity is None:
        abort(404, description=f"No activity with id '{activity_id}'")

    body = request.get_json(force=True) or {}
    response_text = (body.get("response") or "").strip()
    if not response_text:
        abort(400, description="response is required")

    kind, prompt_text = _feedback_kind_and_prompt(activity)
    if kind is None:
        abort(400, description=f"Activity type '{activity.activity_type}' doesn't take free-text feedback")

    settings = UserSettings.get_or_create()
    try:
        feedback = generate_activity_feedback(
            prompt_text,
            response_text,
            kind,
            settings.feedback_tone,
            course_id=activity.module.course_id,
            module_id=activity.module_id,
        )
    except LLMOutputValidationError:
        abort(502, description="Failed to generate feedback")

    # Feedback itself is never persisted (regenerated fresh each time) - this
    # commit exists solely to save the LLMUsageLog row generate_activity_feedback()
    # added to the session (see llm.py's complete()).
    db.session.commit()

    return jsonify({"feedback": feedback})


def _feedback_kind_and_prompt(activity: Activity) -> tuple[str | None, str]:
    content = activity.to_dict()
    if activity.activity_type in ("essay", "project", "capstone"):
        return activity.activity_type, content.get("prompt") or ""
    return None, ""


@activities_bp.post("/api/activities/<activity_id>/discussion-messages")
def post_discussion_message(activity_id: str) -> Response:
    """Submit a reply in a discussion activity's real, multi-turn conversation.

    Args:
        activity_id: The activity's id.

    Returns:
        {"done": bool, "message": str} - Bonsai's next turn (or closing
        reply, once done).

    Raises:
        400: If the activity isn't a discussion, it's already finished, or
            the request has no non-empty "message".
        404: If no activity matches activity_id.
        502: If the LLM's response doesn't match DiscussionTurnSchema.
    """
    activity = db.session.get(Activity, activity_id)
    if activity is None:
        abort(404, description=f"No activity with id '{activity_id}'")

    body = request.get_json(force=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        abort(400, description="message is required")

    try:
        turn = generate_discussion_reply(activity, message)
    except DiscussionNotAvailableError as e:
        abort(400, description=str(e))
    except LLMOutputValidationError:
        abort(502, description="Failed to generate a discussion reply")

    db.session.commit()

    return jsonify({"done": turn.done, "message": turn.message})
