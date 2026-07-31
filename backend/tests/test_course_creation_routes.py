"""Tests for the course-creation REST routes (interview -> outline -> approve)."""


def test_start_course_returns_course_id_and_first_question(client, db) -> None:
    response = client.post("/api/courses", json={"message": "I want to learn GPU programming"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["courseId"]
    assert body["done"] is False
    assert body["question"]


def test_submit_interview_answer_returns_next_question(client, db) -> None:
    start = client.post("/api/courses", json={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(f"/api/courses/{start['courseId']}/interview-messages", json={"answer": "I'm a beginner"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["done"] is False
    assert body["question"] != start["question"]


def test_submit_interview_answer_404s_for_unknown_course(client, db) -> None:
    response = client.post("/api/courses/does-not-exist/interview-messages", json={"answer": "hi"})

    assert response.status_code == 404


def test_generate_outline_returns_course_with_modules(client, db) -> None:
    start = client.post("/api/courses", json={"message": "I want to learn GPU programming"}).get_json()

    response = client.post(f"/api/courses/{start['courseId']}/generate-outline")

    assert response.status_code == 200
    body = response.get_json()
    assert body["stage"] == "outline_review"
    assert len(body["modules"]) > 0


def test_outline_feedback_regenerates_the_outline(client, db) -> None:
    start = client.post("/api/courses", json={"message": "I want to learn GPU programming"}).get_json()
    original = client.post(f"/api/courses/{start['courseId']}/generate-outline").get_json()

    response = client.post(
        f"/api/courses/{start['courseId']}/outline-feedback", json={"feedback": "add more on memory"}
    )

    assert response.status_code == 200
    assert response.get_json()["title"] != original["title"]


def test_approve_outline_activates_the_course(client, db) -> None:
    start = client.post("/api/courses", json={"message": "I want to learn GPU programming"}).get_json()
    client.post(f"/api/courses/{start['courseId']}/generate-outline")

    response = client.post(f"/api/courses/{start['courseId']}/approve-outline")

    assert response.status_code == 200
    body = response.get_json()
    assert body["stage"] == "active"
    assert body["modules"][0]["status"] == "in_progress"
