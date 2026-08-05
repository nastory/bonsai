"""Tests for the activity-completion route."""

from datetime import datetime, timedelta

from app.models import Activity, Course, Module


def _seed_course_with_two_modules(db) -> None:
    course = Course(
        id="c1", title="T", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    module1 = Module(
        id="m1", position=0, title="M1", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    module1.activities = [
        Activity(id="a1", position=0, activity_type="reading", title="A1", status="available"),
        Activity(id="a2", position=1, activity_type="reading", title="A2", status="available"),
    ]
    module2 = Module(
        id="m2", position=1, title="M2", description="d",
        estimated_timeline="1 week", status="locked", learning_outcomes=[],
    )
    # No activities: a locked module hasn't been generated yet at all,
    # unlike an activity within an already-generated module.
    course.modules = [module1, module2]
    db.session.add(course)
    db.session.commit()


def _find_activity(body, activity_id):
    return next(a for m in body["modules"] for a in m["activities"] if a["id"] == activity_id)


def _find_module(body, module_id):
    return next(m for m in body["modules"] if m["id"] == module_id)


def test_complete_activity_marks_it_completed_without_touching_course_stage(client, db) -> None:
    _seed_course_with_two_modules(db)

    response = client.post("/api/activities/a1/complete")

    assert response.status_code == 200
    body = response.get_json()
    assert _find_activity(body, "a1")["status"] == "completed"
    assert body["stage"] == "active"


def test_complete_activity_sets_completed_at(client, db) -> None:
    _seed_course_with_two_modules(db)
    before = datetime.utcnow() - timedelta(seconds=5)

    response = client.post("/api/activities/a1/complete")

    completed_at = _find_activity(response.get_json(), "a1")["completedAt"]
    assert completed_at is not None
    assert datetime.fromisoformat(completed_at) >= before


def test_completing_activity_does_not_lock_or_change_sibling_activities(client, db) -> None:
    # All of a module's activities are generated together and available from
    # the start; completing one must not cascade a lock/unlock onto others.
    _seed_course_with_two_modules(db)

    response = client.post("/api/activities/a1/complete")

    assert _find_activity(response.get_json(), "a2")["status"] == "available"


def test_completing_last_activity_completes_module_unlocks_next_and_leaves_course_stage_unchanged(client, db) -> None:
    _seed_course_with_two_modules(db)
    client.post("/api/activities/a1/complete")

    response = client.post("/api/activities/a2/complete")

    body = response.get_json()
    assert _find_module(body, "m1")["status"] == "completed"
    assert _find_module(body, "m2")["status"] == "in_progress"
    assert body["stage"] == "active"


def test_complete_activity_persists_across_requests(client, db) -> None:
    _seed_course_with_two_modules(db)
    client.post("/api/activities/a1/complete")

    response = client.get("/api/courses/c1")

    assert _find_activity(response.get_json(), "a1")["status"] == "completed"


def test_complete_unknown_activity_returns_404(client, db) -> None:
    response = client.post("/api/activities/does-not-exist/complete")

    assert response.status_code == 404


def test_completing_last_activity_of_last_module_marks_course_completed(client, db) -> None:
    course = Course(
        id="c2", title="T", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    module = Module(
        id="m3", position=0, title="M1", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    module.activities = [
        Activity(id="a3", position=0, activity_type="reading", title="A1", status="available"),
    ]
    course.modules = [module]
    db.session.add(course)
    db.session.commit()

    response = client.post("/api/activities/a3/complete")

    body = response.get_json()
    assert _find_module(body, "m3")["status"] == "completed"
    assert body["stage"] == "completed"
