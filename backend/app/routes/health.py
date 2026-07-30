"""Health check endpoint."""

from flask import Blueprint, Response, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health() -> Response:
    """Report that the backend is up.

    Returns:
        A JSON response of the form ``{"status": "ok"}``.
    """
    return jsonify({"status": "ok"})
