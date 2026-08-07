"""Tests for real, multi-turn discussion generation (app/services/discussion.py)."""

import pytest

from app.extensions import db as _db
from app.models import Activity, Course, ConversationMessage, Module, UserSettings
from app.services.content_storage import save_activity_content
from app.services.discussion import (
    MAX_DISCUSSION_TURNS,
    TARGET_DISCUSSION_TURNS,
    DiscussionNotAvailableError,
    generate_discussion_reply,
)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _seed_discussion_activity(activity_id: str = "a1") -> Activity:
    course = Course(
        id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x"
    )
    module = Module(
        id="m1", position=0, title="M1", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    activity = Activity(id=activity_id, position=0, activity_type="discussion", title="A1", status="available")
    activity.content_path = save_activity_content(activity_id, {"prompt": "What do you think about X?"})
    module.activities = [activity]
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return _db.session.get(Activity, activity_id)


def test_mock_mode_returns_a_reply_before_the_target_turn(app, db) -> None:
    with app.app_context():
        activity = _seed_discussion_activity()

        result = generate_discussion_reply(activity, "My first reply.")

        assert result.done is False
        assert result.message


def test_mock_mode_finishes_at_the_target_turn(app, db) -> None:
    with app.app_context():
        _seed_discussion_activity()

        # Re-fetch each turn and commit between them, mirroring how the real
        # route gets a fresh Activity per HTTP request - reusing the same
        # in-memory object across turns would see a stale, once-loaded
        # conversation_messages collection instead of each turn's new rows.
        result = None
        for i in range(TARGET_DISCUSSION_TURNS):
            activity = _db.session.get(Activity, "a1")
            result = generate_discussion_reply(activity, f"Reply {i + 1}.")
            _db.session.commit()

        assert result.done is True


def test_final_message_tells_the_learner_the_activity_is_complete(app, db) -> None:
    with app.app_context():
        _seed_discussion_activity()

        result = None
        for i in range(TARGET_DISCUSSION_TURNS):
            activity = _db.session.get(Activity, "a1")
            result = generate_discussion_reply(activity, f"Reply {i + 1}.")
            _db.session.commit()

        assert "you've completed this activity" in result.message.lower()


def test_non_final_messages_do_not_include_the_completion_note(app, db) -> None:
    with app.app_context():
        activity = _seed_discussion_activity()

        result = generate_discussion_reply(activity, "My first reply.")

        assert result.done is False
        assert "completed this activity" not in result.message.lower()


def test_persists_the_learner_reply_and_bonsais_message(app, db) -> None:
    with app.app_context():
        activity = _seed_discussion_activity()

        generate_discussion_reply(activity, "My first reply.")

        messages = ConversationMessage.query.filter_by(activity_id="a1").order_by(ConversationMessage.id).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "My first reply."
        assert messages[0].kind == "discussion_reply"
        assert messages[1].role == "assistant"


def test_final_turn_is_persisted_with_wrapup_kind(app, db) -> None:
    with app.app_context():
        _seed_discussion_activity()

        for i in range(TARGET_DISCUSSION_TURNS):
            activity = _db.session.get(Activity, "a1")
            generate_discussion_reply(activity, f"Reply {i + 1}.")
            _db.session.commit()

        messages = ConversationMessage.query.filter_by(activity_id="a1").order_by(ConversationMessage.id).all()
        assert messages[-1].kind == "discussion_wrapup"
        assert messages[-1].role == "assistant"


def test_raises_when_activity_is_not_a_discussion(app, db) -> None:
    with app.app_context():
        course = Course(
            id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x"
        )
        module = Module(
            id="m1", position=0, title="M1", description="d",
            estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
        )
        activity = Activity(id="a1", position=0, activity_type="essay", title="A1", status="available")
        activity.content_path = save_activity_content("a1", {"prompt": "Reflect on X."})
        module.activities = [activity]
        course.modules = [module]
        _db.session.add(course)
        _db.session.commit()

        with pytest.raises(DiscussionNotAvailableError):
            generate_discussion_reply(_db.session.get(Activity, "a1"), "reply")


def test_raises_once_the_discussion_has_already_finished(app, db) -> None:
    with app.app_context():
        _seed_discussion_activity()

        for i in range(TARGET_DISCUSSION_TURNS):
            activity = _db.session.get(Activity, "a1")
            generate_discussion_reply(activity, f"Reply {i + 1}.")
            _db.session.commit()

        with pytest.raises(DiscussionNotAvailableError):
            generate_discussion_reply(_db.session.get(Activity, "a1"), "one more reply")


def test_real_mode_sends_turn_count_and_tone_to_the_prompt(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        activity = _seed_discussion_activity()
        settings = UserSettings.get_or_create()
        settings.feedback_tone = "straightforward"
        _db.session.commit()

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse('{"reflection": "still going", "done": false, "message": "A real follow-up."}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        result = generate_discussion_reply(activity, "My real reply.")

        assert result.done is False
        assert result.message == "A real follow-up."
        system_prompt = captured["messages"][0]["content"]
        assert "Direct and concise" in system_prompt
        assert "What do you think about X?" in system_prompt
        assert "My real reply." in captured["messages"][-1]["content"]


def test_real_mode_enforces_the_hard_cap_even_if_the_model_says_not_done(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        _seed_discussion_activity()

        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"reflection": "keeps going", "done": false, "message": "Another question?"}'),
        )

        result = None
        for i in range(MAX_DISCUSSION_TURNS):
            result = generate_discussion_reply(_db.session.get(Activity, "a1"), f"Reply {i + 1}.")
            _db.session.commit()

        assert result.done is True
