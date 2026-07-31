"""Read-only routes for course data.

There's no course-creation endpoint yet; courses only exist here once a
later slice wires up the real LLM-driven creation flow.
"""

from flask import Blueprint, abort, jsonify
from flask.wrappers import Response

from app.extensions import db
from app.models import Course

courses_bp = Blueprint("courses", __name__)


@courses_bp.get("/api/courses")
def list_courses() -> Response:
    """List all courses.

    Returns:
        A JSON array of serialized courses, in no particular order.
    """
    courses = db.session.execute(db.select(Course)).scalars().all()
    return jsonify([course.to_dict() for course in courses])


@courses_bp.get("/api/courses/<course_id>")
def get_course(course_id: str) -> Response:
    """Get one course's full detail, including nested modules and activities.

    Args:
        course_id: The course's id.

    Returns:
        The serialized course.
    """
    course = db.session.get(Course, course_id)
    if course is None:
        abort(404, description=f"No course with id '{course_id}'")
    return jsonify(course.to_dict())
