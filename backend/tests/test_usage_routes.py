"""Tests for the /api/usage routes."""

from app.extensions import db as _db
from app.models import Course, LLMUsageLog
from app.services.llm_pricing import REFERENCE_MODELS


def _seed_course(course_id: str, title: str) -> None:
    _db.session.add(
        Course(
            id=course_id,
            title=title,
            description="d",
            prerequisites=[],
            estimated_timeline="1 week",
            thumbnail_url="x",
        )
    )


def _log(course_id: str, prompt_tokens: int, completion_tokens: int) -> None:
    _db.session.add(
        LLMUsageLog(
            course_id=course_id,
            call_type="course_outline",
            model="claude-3-5-sonnet-20241022",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    )


def test_get_usage_aggregates_across_courses(client, db) -> None:
    _seed_course("c1", "Course One")
    _seed_course("c2", "Course Two")
    _log("c1", 100, 20)
    _log("c2", 50, 10)
    db.session.commit()

    response = client.get("/api/usage")

    assert response.status_code == 200
    body = response.get_json()
    assert body["courseId"] is None
    assert body["totalTokens"] == 180
    assert len(body["byCourse"]) == 2


def test_get_course_usage_scopes_to_one_course(client, db) -> None:
    _seed_course("c1", "Course One")
    _log("c1", 100, 20)
    db.session.commit()

    response = client.get("/api/courses/c1/usage")

    assert response.status_code == 200
    body = response.get_json()
    assert body["courseId"] == "c1"
    assert body["totalTokens"] == 120


def test_get_course_usage_returns_404_for_unknown_course(client, db) -> None:
    response = client.get("/api/courses/nonexistent/usage")

    assert response.status_code == 404


def test_get_reference_models_lists_the_catalog(client, db) -> None:
    response = client.get("/api/usage/reference-models")

    assert response.status_code == 200
    body = response.get_json()
    assert {entry["name"] for entry in body} == set(REFERENCE_MODELS)
    assert {entry["model"] for entry in body} == set(REFERENCE_MODELS.values())
