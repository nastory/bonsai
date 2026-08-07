"""Tests for the "Change This Course" mid-course direction-change flow.

Interview -> proposed modules -> (optional revision) -> approve. Nothing
about the course's remaining modules is touched until approve_direction_change()
commits — this mirrors, but doesn't reuse, the course-creation interview ->
outline -> approve flow, since an already-active course has no "not live
yet" stage to hold a pending proposal in the way a not-yet-approved new
course does.
"""

from pathlib import Path

import pytest

from app.extensions import db
from app.models import Activity, ConversationMessage, Course, Module
from app.services.content_storage import save_activity_content
from app.services.course_generation import (
    MAX_INTERVIEW_QUESTIONS,
    approve_direction_change,
    generate_direction_change_outline,
    start_direction_change,
    submit_direction_change_answer,
    submit_direction_change_feedback,
)
from app.services.module_generation import ModuleNotFoundError


def _make_course_with_modules(app) -> Course:
    course = Course(
        id="c1",
        title="GPU Programming",
        description="d",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="x",
        stage="active",
    )
    completed = Module(
        id="m0",
        course_id="c1",
        position=0,
        title="Basics",
        description="d",
        estimated_timeline="1 week",
        status="completed",
        learning_outcomes=[],
    )
    content_path = save_activity_content("a0", {"body": "Some reading content."})
    completed.activities = [
        Activity(
            id="a0", module_id="m0", position=0, activity_type="reading", title="Intro",
            status="completed", estimated_minutes=10, content_path=content_path,
        )
    ]
    remaining = [
        Module(
            id=f"m{i}", course_id="c1", position=i, title=f"Module {i}", description="d",
            estimated_timeline="1 week", status="in_progress" if i == 1 else "locked", learning_outcomes=[],
        )
        for i in (1, 2)
    ]
    course.modules = [completed, *remaining]
    db.session.add_all(
        [course, ConversationMessage(course_id="c1", module_id="m0", role="assistant", kind="module_learning_digest", content="Covered the basics.")]
    )
    db.session.commit()
    return course


def test_start_direction_change_records_message_and_asks_a_question(app, db) -> None:
    with app.app_context():
        _make_course_with_modules(app)

        step = start_direction_change("m0", "I want to focus more on hardware internals")

        assert step.done is False
        assert step.question
        contents = [m.content for m in db.session.get(Course, "c1").conversation if m.module_id == "m0"]
        assert "I want to focus more on hardware internals" in contents


def test_start_direction_change_raises_for_unknown_module(app, db) -> None:
    with app.app_context():
        with pytest.raises(ModuleNotFoundError):
            start_direction_change("does-not-exist", "message")


def test_submit_direction_change_answer_continues_the_interview(app, db) -> None:
    with app.app_context():
        _make_course_with_modules(app)
        start_direction_change("m0", "I want to focus more on hardware internals")

        step = submit_direction_change_answer("m0", "Something more advanced")

        assert step.question is not None
        questions = [
            m.content
            for m in db.session.get(Course, "c1").conversation
            if m.module_id == "m0" and m.kind == "direction_interview_question"
        ]
        assert len(questions) >= 1


def test_direction_interview_stops_after_max_questions(app, db) -> None:
    with app.app_context():
        _make_course_with_modules(app)
        step = start_direction_change("m0", "I want to focus more on hardware internals")

        for _ in range(MAX_INTERVIEW_QUESTIONS):
            step = submit_direction_change_answer("m0", "more detail")

        assert step.done is True
        assert step.question is None


def test_generate_direction_change_outline_does_not_touch_existing_modules(app, db) -> None:
    with app.app_context():
        course = _make_course_with_modules(app)
        start_direction_change("m0", "I want to focus more on hardware internals")

        proposal = generate_direction_change_outline("m0")

        assert len(proposal.modules) >= 1
        assert [m.id for m in course.modules] == ["m0", "m1", "m2"]  # untouched until approval


def test_submit_direction_change_feedback_revises_the_proposal(app, db) -> None:
    with app.app_context():
        _make_course_with_modules(app)
        start_direction_change("m0", "I want to focus more on hardware internals")
        generate_direction_change_outline("m0")

        revised = submit_direction_change_feedback("m0", "Make it shorter")

        assert "(revised)" in revised.modules[0].title
        presented = [
            m
            for m in db.session.get(Course, "c1").conversation
            if m.module_id == "m0" and m.kind == "direction_outline_presented"
        ]
        assert len(presented) == 2


def test_approve_direction_change_replaces_remaining_modules(app, db) -> None:
    with app.app_context():
        course = _make_course_with_modules(app)
        start_direction_change("m0", "I want to focus more on hardware internals")
        generate_direction_change_outline("m0")

        updated = approve_direction_change("m0")

        ids = [m.id for m in updated.modules]
        assert "m1" not in ids
        assert "m2" not in ids
        assert ids[0] == "m0"
        new_modules = [m for m in updated.modules if m.id != "m0"]
        assert len(new_modules) >= 1
        assert new_modules[0].position == 1
        assert new_modules[0].status == "in_progress"
        assert all(m.status == "locked" for m in new_modules[1:])


def test_approve_direction_change_preserves_the_completed_module_and_its_activity(app, db) -> None:
    with app.app_context():
        course = _make_course_with_modules(app)
        start_direction_change("m0", "I want to focus more on hardware internals")
        generate_direction_change_outline("m0")

        approve_direction_change("m0")

        preserved = db.session.get(Module, "m0")
        assert preserved is not None
        assert preserved.status == "completed"
        assert len(preserved.activities) == 1
        assert preserved.activities[0].status == "completed"
        content_path = preserved.activities[0].content_path
        assert (Path(app.instance_path) / content_path).exists()


def test_approve_direction_change_raises_without_a_proposal(app, db) -> None:
    with app.app_context():
        _make_course_with_modules(app)

        with pytest.raises(ModuleNotFoundError):
            approve_direction_change("m0")


def test_approve_direction_change_raises_for_unknown_module(app, db) -> None:
    with app.app_context():
        with pytest.raises(ModuleNotFoundError):
            approve_direction_change("does-not-exist")


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_direction_interview_prompt_includes_learning_history_and_real_turns(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        _make_course_with_modules(real_llm_app)

        captured: list = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return _FakeResponse('{"coverage": "open", "done": false, "question": "another question"}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        start_direction_change("m0", "I want to focus more on hardware internals")
        submit_direction_change_answer("m0", "Something more advanced")

        second_call = captured[1]
        assert second_call[0]["role"] == "system"
        assert "Covered the basics." in second_call[0]["content"]
        assert "${" not in second_call[0]["content"]
        assert second_call[1] == {"role": "user", "content": "I want to focus more on hardware internals"}
        assert second_call[2] == {"role": "assistant", "content": "another question"}
        assert second_call[3] == {"role": "user", "content": "Something more advanced"}


def test_direction_outline_prompt_includes_learning_history(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        _make_course_with_modules(real_llm_app)

        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        )
        start_direction_change("m0", "I want to focus more on hardware internals")

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse(
                '{"modules": [{"title": "T", "description": "d", "estimatedTimeline": "1 week", '
                '"learningOutcomes": [], "plannedActivities": []}]}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_direction_change_outline("m0")

        assert "Covered the basics." in captured["prompt"]


def test_direction_outline_prompt_includes_activity_usage_summary(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        _make_course_with_modules(real_llm_app)

        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        )
        start_direction_change("m0", "I want to focus more on hardware internals")

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse(
                '{"modules": [{"title": "T", "description": "d", "estimatedTimeline": "1 week", '
                '"learningOutcomes": [], "plannedActivities": []}]}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_direction_change_outline("m0")

        assert "1 reading" in captured["prompt"]


def test_activity_type_usage_summary_counts_generated_activities_up_to_the_given_position(app, db) -> None:
    from app.services.course_generation import _activity_type_usage_summary

    with app.app_context():
        course = _make_course_with_modules(app)

        summary = _activity_type_usage_summary(course, up_to_module_position=0)

        assert summary == "Activity types already used earlier in this course: 1 reading"


def test_activity_type_usage_summary_falls_back_when_nothing_generated_yet(app, db) -> None:
    from app.services.course_generation import _activity_type_usage_summary

    with app.app_context():
        course = Course(
            id="c2", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x"
        )
        module = Module(
            id="m0", course_id="c2", position=0, title="M", description="d",
            estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
        )
        course.modules = [module]
        db.session.add(course)
        db.session.commit()

        summary = _activity_type_usage_summary(course, up_to_module_position=0)

        assert summary == "No activities have been generated yet in this course."
