"""Tests for /api/activities/<id>/discussion-messages: the real, multi-turn discussion endpoint."""

from app.extensions import db as _db
from app.models import Activity, Course, Module
from app.services.content_storage import save_activity_content
from app.services.discussion import TARGET_DISCUSSION_TURNS


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _seed_activity(activity_id: str, activity_type: str, content: dict) -> None:
    course = Course(
        id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x"
    )
    module = Module(
        id="m1", position=0, title="M1", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    activity = Activity(id=activity_id, position=0, activity_type=activity_type, title="A1", status="available")
    activity.content_path = save_activity_content(activity_id, content)
    module.activities = [activity]
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()


def test_discussion_message_mock_mode_returns_a_reply(client, db) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})

    response = client.post("/api/activities/a1/discussion-messages", json={"message": "My reply."})

    assert response.status_code == 200
    body = response.get_json()
    assert "done" in body
    assert body["message"]


def test_discussion_message_persists_across_requests(client, db) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})

    client.post("/api/activities/a1/discussion-messages", json={"message": "My reply."})
    response = client.get("/api/courses/c1")

    activity = next(a for m in response.get_json()["modules"] for a in m["activities"] if a["id"] == "a1")
    assert len(activity["messages"]) == 2
    assert activity["messages"][0]["content"] == "My reply."
    assert activity["discussionDone"] is False


def test_discussion_message_marks_discussion_done_once_finished(client, db) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})

    for i in range(TARGET_DISCUSSION_TURNS):
        response = client.post("/api/activities/a1/discussion-messages", json={"message": f"Reply {i + 1}."})

    assert response.get_json()["done"] is True
    course = client.get("/api/courses/c1").get_json()
    activity = next(a for m in course["modules"] for a in m["activities"] if a["id"] == "a1")
    assert activity["discussionDone"] is True


def test_discussion_message_rejects_non_discussion_activity(client, db) -> None:
    _seed_activity("a1", "essay", {"prompt": "Reflect on X."})

    response = client.post("/api/activities/a1/discussion-messages", json={"message": "My reply."})

    assert response.status_code == 400


def test_discussion_message_rejects_empty_message(client, db) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})

    response = client.post("/api/activities/a1/discussion-messages", json={"message": "   "})

    assert response.status_code == 400


def test_discussion_message_rejects_once_already_finished(client, db) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})
    for i in range(TARGET_DISCUSSION_TURNS):
        client.post("/api/activities/a1/discussion-messages", json={"message": f"Reply {i + 1}."})

    response = client.post("/api/activities/a1/discussion-messages", json={"message": "one more"})

    assert response.status_code == 400


def test_discussion_message_unknown_activity_returns_404(client, db) -> None:
    response = client.post("/api/activities/does-not-exist/discussion-messages", json={"message": "hi"})

    assert response.status_code == 404


def test_discussion_message_returns_502_on_malformed_llm_response(real_llm_client, monkeypatch) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json"))

    response = real_llm_client.post("/api/activities/a1/discussion-messages", json={"message": "My reply."})

    assert response.status_code == 502
