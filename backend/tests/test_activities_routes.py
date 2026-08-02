"""Tests for the activity-completion route."""

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


def test_complete_activity_marks_it_completed(client, db) -> None:
    _seed_course_with_two_modules(db)

    response = client.post("/api/activities/a1/complete")

    assert response.status_code == 200
    assert _find_activity(response.get_json(), "a1")["status"] == "completed"


def test_completing_activity_does_not_lock_or_change_sibling_activities(client, db) -> None:
    # All of a module's activities are generated together and available from
    # the start; completing one must not cascade a lock/unlock onto others.
    _seed_course_with_two_modules(db)

    response = client.post("/api/activities/a1/complete")

    assert _find_activity(response.get_json(), "a2")["status"] == "available"


def test_completing_last_activity_completes_module_and_unlocks_next_module(client, db) -> None:
    _seed_course_with_two_modules(db)
    client.post("/api/activities/a1/complete")

    response = client.post("/api/activities/a2/complete")

    body = response.get_json()
    assert _find_module(body, "m1")["status"] == "completed"
    assert _find_module(body, "m2")["status"] == "in_progress"


def test_complete_activity_persists_across_requests(client, db) -> None:
    _seed_course_with_two_modules(db)
    client.post("/api/activities/a1/complete")

    response = client.get("/api/courses/c1")

    assert _find_activity(response.get_json(), "a1")["status"] == "completed"


def test_complete_unknown_activity_returns_404(client, db) -> None:
    response = client.post("/api/activities/does-not-exist/complete")

    assert response.status_code == 404
