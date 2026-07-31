"""Tests for the health check endpoint."""

from flask.testing import FlaskClient


def test_health_check_returns_ok(client: FlaskClient) -> None:
    """GET /api/health reports the backend is up."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
