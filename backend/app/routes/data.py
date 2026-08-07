"""Routes for exporting/importing a learner's full data archive."""

import io

from flask import Blueprint, abort, jsonify, request, send_file
from flask.wrappers import Response

from app.services.course_generation import reset_all_data
from app.services.data_export import DataImportError, export_data, import_data

data_bp = Blueprint("data", __name__)


@data_bp.get("/api/data/export")
def get_export() -> Response:
    """Download a .zip archive of everything except credentials.

    Returns:
        The archive as an application/zip attachment.
    """
    archive_bytes = export_data()
    return send_file(
        io.BytesIO(archive_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name="bonsai-export.zip",
    )


@data_bp.post("/api/data/import")
def post_import() -> Response:
    """Restore courses/progress/settings from a previously exported archive.

    Multipart form data: `file` (the .zip archive).

    Returns:
        An empty JSON object on success, or a 422 with an error message if
        the archive isn't a valid Bonsai export.
    """
    file = request.files.get("file")
    if file is None:
        abort(400, description="No file uploaded")
    try:
        import_data(file.read())
    except DataImportError as e:
        return jsonify({"error": str(e)}), 422
    return jsonify({})


@data_bp.post("/api/data/reset")
def post_reset() -> Response:
    """Permanently delete every course and all learner data, and reset Settings to defaults.

    Body: {"confirm": "delete"} - the server re-checks this itself rather
    than trusting the frontend's own confirmation UI alone, since this is
    irreversible. Anything else (missing, misspelled, wrong case) is
    rejected without touching any data.

    Returns:
        An empty JSON object on success.
    """
    body = request.get_json(silent=True) or {}
    if body.get("confirm") != "delete":
        abort(400, description="Type 'delete' to confirm - nothing was deleted")
    reset_all_data()
    return jsonify({})
