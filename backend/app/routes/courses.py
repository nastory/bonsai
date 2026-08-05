"""Routes for course data: listing/fetching, plus deletion.

Creation (interview -> outline -> approve) lives in course_creation.py.
"""

from flask import Blueprint, abort, jsonify, send_file
from flask.wrappers import Response

from app.extensions import db
from app.models import Course
from app.services.course_generation import CourseNotFoundError, delete_course
from app.services.thumbnail_storage import resolve_thumbnail_image_path

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


@courses_bp.get("/api/courses/<course_id>/thumbnail")
def get_course_thumbnail(course_id: str) -> Response:
    """Serve a course's generated thumbnail image, if one exists.

    Args:
        course_id: The course's id.

    Returns:
        The image bytes (PNG), served inline (not as a download).
    """
    course = db.session.get(Course, course_id)
    if course is None or not course.thumbnail_image_path:
        abort(404, description=f"No generated thumbnail for course '{course_id}'")
    return send_file(resolve_thumbnail_image_path(course.thumbnail_image_path), mimetype="image/png")


@courses_bp.delete("/api/courses/<course_id>")
def delete_course_route(course_id: str) -> Response:
    """Permanently delete a course, including its modules, activities, and stored content.

    Args:
        course_id: The course's id.

    Returns:
        An empty JSON object on success.
    """
    try:
        delete_course(course_id)
    except CourseNotFoundError:
        abort(404, description=f"No course with id '{course_id}'")
    return jsonify({})
