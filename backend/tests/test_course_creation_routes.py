"""Tests for the course-creation REST routes (interview -> outline -> approve)."""

from io import BytesIO


def test_start_course_returns_course_id_and_first_question(client, db) -> None:
    response = client.post("/api/courses", data={"message": "I want to learn GPU programming"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["courseId"]
    assert body["done"] is False
    assert body["question"]


def test_start_course_with_parent_course_id_sets_lineage(client, db) -> None:
    parent = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(
        "/api/courses",
        data={"message": "I want to go deeper on memory coalescing", "parentCourseId": parent["courseId"]},
    )

    assert response.status_code == 201
    course = client.get(f"/api/courses/{response.get_json()['courseId']}").get_json()
    assert course["parentCourseId"] == parent["courseId"]


def test_start_course_with_unknown_parent_course_id_returns_404(client, db) -> None:
    response = client.post(
        "/api/courses",
        data={"message": "I want to go deeper", "parentCourseId": "does-not-exist"},
    )

    assert response.status_code == 404


def test_start_course_with_an_attached_file_persists_a_source_material(client, db) -> None:
    response = client.post(
        "/api/courses",
        data={
            "message": "I want to learn about this paper",
            "files": (BytesIO(b"GPU memory coalescing improves throughput."), "notes.txt"),
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert len(body["sourceMaterials"]) == 1
    assert body["sourceMaterials"][0]["fileName"] == "notes.txt"


def test_start_course_with_an_unsupported_file_returns_422_and_persists_nothing(client, db) -> None:
    from app.models import Course

    response = client.post(
        "/api/courses",
        data={
            "message": "I want to learn about this paper",
            "files": (BytesIO(b"some content"), "notes.rtf"),
        },
    )

    assert response.status_code == 422
    assert "error" in response.get_json()
    # Nothing was actually committed (db.session.commit() is never reached
    # on this path): autoflush can make an uncommitted insert visible
    # mid-transaction, so roll back first to confirm nothing durable happened.
    db.session.rollback()
    assert db.session.execute(db.select(Course)).first() is None


def test_submit_interview_answer_with_an_attached_file_persists_a_source_material(client, db) -> None:
    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(
        f"/api/courses/{start['courseId']}/interview-messages",
        data={
            "answer": "here's a paper",
            "files": (BytesIO(b"Efficient memory coalescing in CUDA kernels."), "paper.txt"),
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["sourceMaterials"]) == 1
    assert body["sourceMaterials"][0]["fileName"] == "paper.txt"


def test_submit_interview_answer_with_an_unsupported_file_persists_no_new_message(client, db) -> None:
    from app.models import ConversationMessage

    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(
        f"/api/courses/{start['courseId']}/interview-messages",
        data={
            "answer": "here's a paper",
            "files": (BytesIO(b"some content"), "notes.rtf"),
        },
    )

    assert response.status_code == 422
    db.session.rollback()
    contents = [
        m.content for m in db.session.execute(db.select(ConversationMessage)).scalars()
    ]
    assert "here's a paper" not in contents


def test_submit_interview_answer_returns_next_question(client, db) -> None:
    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(f"/api/courses/{start['courseId']}/interview-messages", data={"answer": "I'm a beginner"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["done"] is False
    assert body["question"] != start["question"]


def test_submit_interview_answer_404s_for_unknown_course(client, db) -> None:
    response = client.post("/api/courses/does-not-exist/interview-messages", data={"answer": "hi"})

    assert response.status_code == 404


def test_generate_outline_returns_course_with_modules(client, db) -> None:
    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(f"/api/courses/{start['courseId']}/generate-outline")

    assert response.status_code == 200
    body = response.get_json()
    assert body["stage"] == "outline_review"
    assert len(body["modules"]) > 0


def test_outline_feedback_regenerates_the_outline(client, db) -> None:
    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()
    original = client.post(f"/api/courses/{start['courseId']}/generate-outline").get_json()

    response = client.post(
        f"/api/courses/{start['courseId']}/outline-feedback", json={"feedback": "add more on memory"}
    )

    assert response.status_code == 200
    assert response.get_json()["title"] != original["title"]


def test_approve_outline_activates_the_course(client, db) -> None:
    start = client.post("/api/courses", data={"message": "I want to learn GPU programming"}).get_json()
    client.post(f"/api/courses/{start['courseId']}/generate-outline")

    response = client.post(f"/api/courses/{start['courseId']}/approve-outline")

    assert response.status_code == 200
    body = response.get_json()
    assert body["stage"] == "active"
    assert body["modules"][0]["status"] == "in_progress"
