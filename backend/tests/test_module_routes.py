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
        activity_plan=[{"type": "reading", "title": "What Is a GPU?", "plan": "Cover the basics."}],
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


def _make_course_with_a_completed_module(course_id: str = "c2") -> Module:
    course = Course(
        id=course_id, title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
    )
    completed = Module(
        id="cm0", course_id=course_id, position=0, title="Basics", description="d",
        estimated_timeline="1 week", status="completed", learning_outcomes=[],
    )
    remaining = Module(
        id="cm1", course_id=course_id, position=1, title="Next Up", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    course.modules = [completed, remaining]
    _db.session.add(course)
    _db.session.commit()
    return completed


def test_direction_change_routes_return_404_for_unknown_module(client, db) -> None:
    assert client.post(
        "/api/modules/does-not-exist/direction-interview", json={"message": "hi"}
    ).status_code == 404
    assert client.post(
        "/api/modules/does-not-exist/direction-interview-messages", json={"answer": "hi"}
    ).status_code == 404
    assert client.post("/api/modules/does-not-exist/direction-outline").status_code == 404
    assert client.post(
        "/api/modules/does-not-exist/direction-outline-feedback", json={"feedback": "shorter"}
    ).status_code == 404
    assert client.post("/api/modules/does-not-exist/direction-outline-approve").status_code == 404


def test_direction_change_full_flow_via_http(client, db) -> None:
    module = _make_course_with_a_completed_module()

    start = client.post(f"/api/modules/{module.id}/direction-interview", json={"message": "I want more depth"})
    assert start.status_code == 200
    assert start.get_json()["done"] is False
    assert start.get_json()["question"]

    answer = client.post(
        f"/api/modules/{module.id}/direction-interview-messages", json={"answer": "more advanced material"}
    )
    assert answer.status_code == 200

    outline = client.post(f"/api/modules/{module.id}/direction-outline")
    assert outline.status_code == 200
    proposal = outline.get_json()
    assert len(proposal["modules"]) >= 1

    feedback = client.post(f"/api/modules/{module.id}/direction-outline-feedback", json={"feedback": "shorter"})
    assert feedback.status_code == 200

    approve = client.post(f"/api/modules/{module.id}/direction-outline-approve")
    assert approve.status_code == 200
    course = approve.get_json()
    assert "cm1" not in [m["id"] for m in course["modules"]]
    assert course["modules"][0]["id"] == "cm0"
    assert course["modules"][0]["status"] == "completed"
