"""Routes for mutating individual learning activities.

There's no separate "modules" or "courses" mutation endpoint for this: the
module-completion cascade that used to live only in the frontend now lives
here, so progress survives a refresh.
"""

from flask import Blueprint, abort, jsonify
from flask.wrappers import Response

from app.extensions import db
from app.models import Activity

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

    module = activity.module
    if all(a.status == "completed" for a in module.activities):
        module.status = "completed"

        course = module.course
        next_module = next((m for m in course.modules if m.position == module.position + 1), None)
        if next_module is not None and next_module.status == "locked":
            next_module.status = "in_progress"

    db.session.commit()

    return jsonify(module.course.to_dict())
