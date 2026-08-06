"""Routes for LLM token usage / hypothetical cost reporting.

See app/services/usage_reporting.py for the aggregation and
app/services/llm_pricing.py for the reference-model pricing catalog.
"""

from flask import Blueprint, abort, jsonify
from flask.wrappers import Response

from app.extensions import db
from app.models import Course
from app.services.llm_pricing import REFERENCE_MODELS
from app.services.usage_reporting import summarize_usage

usage_bp = Blueprint("usage", __name__)


@usage_bp.get("/api/usage")
def get_usage() -> Response:
    """Aggregate logged LLM usage across every course.

    Returns:
        Totals plus breakdowns by content type, call type, module, and course.
    """
    return jsonify(summarize_usage())


@usage_bp.get("/api/courses/<course_id>/usage")
def get_course_usage(course_id: str) -> Response:
    """Aggregate logged LLM usage for one course.

    Args:
        course_id: The course's id.

    Returns:
        Totals plus breakdowns by content type, call type, and module.
    """
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404, description=f"No course with id '{course_id}'")
    return jsonify(summarize_usage(course_id))


@usage_bp.get("/api/usage/reference-models")
def get_reference_models() -> Response:
    """List the reference models estimated costs are computed against.

    Returns:
        A JSON array of {"name": ..., "model": ...}, one per REFERENCE_MODELS entry.
    """
    return jsonify([{"name": name, "model": key} for name, key in REFERENCE_MODELS.items()])
