"""Tests for /api/activities/<id>/feedback: real feedback on a learner's free-text response.

Covers essay/project/discussion activities and a reading's checkPrompt
comprehension check - the activities that used to get fixed canned copy
regardless of what was actually written (see the deleted frontend
lib/feedback.ts). Quiz/assessment activities reject this endpoint entirely:
they already have real per-question feedback from generation.
"""

from app.extensions import db as _db
from app.models import Activity, Course, Module, UserSettings
from app.services.content_storage import save_activity_content


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
        id="c1", title="T", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
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


def test_feedback_mock_mode_returns_canned_result_referencing_kind(client, db) -> None:
    _seed_activity("a1", "essay", {"prompt": "Reflect on X."})

    response = client.post("/api/activities/a1/feedback", json={"response": "My real answer."})

    assert response.status_code == 200
    assert "essay" in response.get_json()["feedback"]


def test_feedback_real_mode_reads_the_activitys_own_prompt_and_the_response(real_llm_client, monkeypatch) -> None:
    _seed_activity("a1", "discussion", {"prompt": "What do you think about X?"})
    captured: dict = {}

    def fake_completion(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _FakeResponse('{"feedback": "Real feedback on your actual answer."}')

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    response = real_llm_client.post(
        "/api/activities/a1/feedback", json={"response": "I think X is important because..."}
    )

    assert response.status_code == 200
    assert response.get_json()["feedback"] == "Real feedback on your actual answer."
    data_message = captured["messages"][1]["content"]
    assert "What do you think about X?" in data_message
    assert "I think X is important because..." in data_message


def test_feedback_uses_the_learners_configured_tone(real_llm_client, monkeypatch) -> None:
    _seed_activity("a1", "essay", {"prompt": "p"})
    UserSettings.get_or_create().feedback_tone = "straightforward"
    _db.session.commit()
    captured: dict = {}

    def fake_completion(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _FakeResponse('{"feedback": "f"}')

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    real_llm_client.post("/api/activities/a1/feedback", json={"response": "r"})

    system_message = captured["messages"][0]["content"]
    assert "Direct and concise" in system_message
    assert "Warm and encouraging" not in system_message


def test_feedback_for_reading_uses_check_prompt(client, db) -> None:
    _seed_activity("a1", "reading", {"body": "Some reading.", "checkPrompt": "What's the key idea?"})

    response = client.post("/api/activities/a1/feedback", json={"response": "It's about Y."})

    assert response.status_code == 200


def test_feedback_rejects_reading_without_a_check_prompt(client, db) -> None:
    _seed_activity("a1", "reading", {"body": "Some reading."})

    response = client.post("/api/activities/a1/feedback", json={"response": "It's about Y."})

    assert response.status_code == 400


def test_feedback_rejects_quiz_activities(client, db) -> None:
    _seed_activity(
        "a1", "quiz", {"question": "q", "options": ["a", "b"], "correctAnswerIndex": 0, "explanation": "e"}
    )

    response = client.post("/api/activities/a1/feedback", json={"response": "a"})

    assert response.status_code == 400


def test_feedback_rejects_empty_response(client, db) -> None:
    _seed_activity("a1", "essay", {"prompt": "p"})

    response = client.post("/api/activities/a1/feedback", json={"response": "   "})

    assert response.status_code == 400


def test_feedback_unknown_activity_returns_404(client, db) -> None:
    response = client.post("/api/activities/does-not-exist/feedback", json={"response": "r"})

    assert response.status_code == 404


def test_feedback_raises_502_on_malformed_llm_response(real_llm_client, monkeypatch) -> None:
    _seed_activity("a1", "essay", {"prompt": "p"})
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json at all"))

    response = real_llm_client.post("/api/activities/a1/feedback", json={"response": "r"})

    assert response.status_code == 502
