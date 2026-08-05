"""Tests for the /api/courses REST routes."""

from app.models import Activity, Course, Module


def _seed_course(db) -> None:
    course = Course(
        id="gpu-programming",
        title="GPU Programming for ML Engineers",
        description="d",
        prerequisites=["Comfortable with Python"],
        estimated_timeline="6 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
    )
    module = Module(
        id="module-1",
        course_id="gpu-programming",
        position=0,
        title="GPU Architecture Fundamentals",
        description="d",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=[],
    )
    activity = Activity(
        id="m1-a1",
        module_id="module-1",
        position=0,
        activity_type="reading",
        title="What Is a GPU, Really?",
        status="available",
        estimated_minutes=15,
    )
    db.session.add_all([course, module, activity])
    db.session.commit()


def test_list_courses_returns_empty_list_when_none_exist(client, db) -> None:
    response = client.get("/api/courses")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_courses_returns_seeded_courses(client, db) -> None:
    _seed_course(db)

    response = client.get("/api/courses")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["id"] == "gpu-programming"
    assert body[0]["progressPercent"] == 0


def test_get_course_returns_full_detail(client, db) -> None:
    _seed_course(db)

    response = client.get("/api/courses/gpu-programming")

    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "GPU Programming for ML Engineers"
    assert len(body["modules"]) == 1
    assert body["modules"][0]["activities"][0]["title"] == "What Is a GPU, Really?"


def test_get_course_returns_404_for_unknown_course(client, db) -> None:
    response = client.get("/api/courses/does-not-exist")

    assert response.status_code == 404


def test_delete_course_removes_it(client, db) -> None:
    _seed_course(db)

    response = client.delete("/api/courses/gpu-programming")

    assert response.status_code == 200
    assert client.get("/api/courses/gpu-programming").status_code == 404
    assert client.get("/api/courses").get_json() == []


def test_delete_course_returns_404_for_unknown_course(client, db) -> None:
    response = client.delete("/api/courses/does-not-exist")

    assert response.status_code == 404


def test_get_course_thumbnail_returns_404_when_none_generated_or_unknown_course(client, db) -> None:
    _seed_course(db)

    assert client.get("/api/courses/gpu-programming/thumbnail").status_code == 404
    assert client.get("/api/courses/does-not-exist/thumbnail").status_code == 404


def test_get_course_thumbnail_serves_the_generated_image(client, db, app) -> None:
    from app.services.thumbnail_storage import save_thumbnail_image

    with app.app_context():
        thumbnail_path = save_thumbnail_image("gpu-programming", b"fake-png-bytes")
    _seed_course(db)
    course = db.session.get(Course, "gpu-programming")
    course.thumbnail_image_path = thumbnail_path
    db.session.commit()

    response = client.get("/api/courses/gpu-programming/thumbnail")

    assert response.status_code == 200
    assert response.data == b"fake-png-bytes"
    assert response.mimetype == "image/png"
