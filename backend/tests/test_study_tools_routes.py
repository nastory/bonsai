"""Tests for /api/modules/<id>/flash-cards and /api/modules/<id>/quiz-set."""

from app.extensions import db as _db
from app.models import Activity, Course, Module
from app.services.content_storage import save_activity_content


def _seed_generated_module(module_id: str = "m1") -> None:
    course = Course(
        id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x",
    )
    module = Module(
        id=module_id, course_id="c1", position=0, title="M", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    activity = Activity(id="a1", module_id=module_id, position=0, activity_type="reading", title="A1", status="available")
    activity.content_path = save_activity_content("a1", {"body": "Some real content."})
    module.activities = [activity]
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()


def _seed_ungenerated_module(module_id: str = "m1") -> None:
    course = Course(
        id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x",
    )
    module = Module(
        id=module_id, course_id="c1", position=0, title="M", description="d",
        estimated_timeline="1 week", status="locked", learning_outcomes=[],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()


def test_post_flash_cards_returns_a_saved_set(client, db) -> None:
    _seed_generated_module()

    response = client.post("/api/modules/m1/flash-cards")

    assert response.status_code == 200
    body = response.get_json()
    assert body["moduleId"] == "m1"
    assert len(body["cards"]) >= 1


def test_post_flash_cards_persists_across_requests(client, db) -> None:
    _seed_generated_module()
    first = client.post("/api/modules/m1/flash-cards").get_json()

    second = client.post("/api/modules/m1/flash-cards").get_json()

    assert first["id"] == second["id"]


def test_post_flash_cards_unknown_module_returns_404(client, db) -> None:
    response = client.post("/api/modules/does-not-exist/flash-cards")

    assert response.status_code == 404


def test_post_flash_cards_ungenerated_module_returns_400(client, db) -> None:
    _seed_ungenerated_module()

    response = client.post("/api/modules/m1/flash-cards")

    assert response.status_code == 400


def test_post_quiz_set_returns_a_saved_set(client, db) -> None:
    _seed_generated_module()

    response = client.post("/api/modules/m1/quiz-set")

    assert response.status_code == 200
    body = response.get_json()
    assert body["moduleId"] == "m1"
    assert len(body["questions"]) >= 1


def test_post_quiz_set_persists_across_requests(client, db) -> None:
    _seed_generated_module()
    first = client.post("/api/modules/m1/quiz-set").get_json()

    second = client.post("/api/modules/m1/quiz-set").get_json()

    assert first["id"] == second["id"]


def test_post_quiz_set_unknown_module_returns_404(client, db) -> None:
    response = client.post("/api/modules/does-not-exist/quiz-set")

    assert response.status_code == 404


def test_post_quiz_set_ungenerated_module_returns_400(client, db) -> None:
    _seed_ungenerated_module()

    response = client.post("/api/modules/m1/quiz-set")

    assert response.status_code == 400
