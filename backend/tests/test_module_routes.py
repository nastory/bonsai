"""Tests for the module content-generation route."""

from app.extensions import db as _db
from app.models import Course, Module


def _make_module(client, course_id: str = "c1") -> Module:
    course = Course(
        id=course_id,
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    module = Module(
        id="m1",
        course_id=course_id,
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_activities_returns_404_for_unknown_module(client, db) -> None:
    response = client.post("/api/modules/does-not-exist/generate-activities")

    assert response.status_code == 404


def test_generate_activities_returns_the_updated_course(client, db) -> None:
    module = _make_module(client)

    response = client.post(f"/api/modules/{module.id}/generate-activities")

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "c1"
    generated_module = next(m for m in data["modules"] if m["id"] == "m1")
    assert len(generated_module["activities"]) >= 1
    assert generated_module["activities"][0]["status"] == "available"
