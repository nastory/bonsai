"""Tests for module content generation.

Reuses the mock/real branching pattern from course_generation.py: mocked
canned activities (one per planned activity, per Module.activity_plan) in
LLM_TEST_MODE, the real complete()/resolve_model_config() path otherwise.
Every generated activity's content-heavy fields are written to disk via
content_storage, matching the hybrid storage model. Generation also
persists a condensed "module_learning_digest" ConversationMessage once the
module's activities are done, feeding later modules' generation.
"""

import pytest

from app.extensions import db as _db
from app.models import ConversationMessage, Course, Module
from app.services.module_generation import ModuleNotFoundError, generate_module_activities


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _make_module(course_id: str = "c1", activity_plan=None) -> Module:
    course = Course(
        id=course_id,
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    module = Module(
        id="m1",
        course_id=course_id,
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
        activity_plan=activity_plan
        or [
            {"type": "reading", "title": "What Is a GPU?", "plan": "Cover the basics."},
            {"type": "discussion", "title": "Reflect and Discuss", "plan": "Reflect on what stood out."},
            {"type": "assessment", "title": "Check Your Understanding", "plan": "Quiz the basics."},
        ],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_module_activities_raises_for_unknown_module(db) -> None:
    with pytest.raises(ModuleNotFoundError):
        generate_module_activities("does-not-exist")


def test_generate_module_activities_populates_one_activity_per_planned_activity(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    assert len(result.activities) == 3
    assert all(a.status == "available" for a in result.activities)
    assert [a.activity_type for a in result.activities] == ["reading", "discussion", "assessment"]


def test_generate_module_activities_assessment_includes_correct_answer_and_explanation(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    assessment = next(a for a in result.activities if a.activity_type == "assessment")
    data = assessment.to_dict()
    assert 0 <= data["correctAnswerIndex"] < len(data["options"])
    assert data["explanation"]


def test_generate_module_activities_writes_content_path_for_each_activity(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    for activity in result.activities:
        assert activity.content_path is not None
        data = activity.to_dict()
        assert "id" in data


def test_generate_module_activities_is_idempotent(db) -> None:
    module = _make_module()

    first = generate_module_activities(module.id)
    first_ids = [a.id for a in first.activities]

    second = generate_module_activities(module.id)

    assert [a.id for a in second.activities] == first_ids


def test_generate_module_activities_persists_a_learning_digest(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    digests = [m for m in result.course.conversation if m.kind == "module_learning_digest"]
    assert len(digests) == 1
    assert digests[0].module_id == module.id
    assert digests[0].role == "assistant"


def test_generate_module_activities_does_not_duplicate_digest_when_already_generated(db) -> None:
    module = _make_module()

    generate_module_activities(module.id)
    generate_module_activities(module.id)

    digests = [
        m for m in _db.session.get(Course, "c1").conversation if m.kind == "module_learning_digest"
    ]
    assert len(digests) == 1


def test_second_module_generation_includes_first_modules_digest_in_its_prompts(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        course = Course(
            id="c1", title="GPU Programming", description="d", prerequisites=[],
            estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
        )
        module_1 = Module(
            id="m1", course_id="c1", position=0, title="Basics", description="d",
            estimated_timeline="1 week", status="completed", learning_outcomes=[],
            activity_plan=[{"type": "reading", "title": "Intro", "plan": "Cover the basics."}],
        )
        module_2 = Module(
            id="m2", course_id="c1", position=1, title="Memory", description="d",
            estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
            activity_plan=[{"type": "reading", "title": "Memory Overview", "plan": "Cover memory."}],
        )
        course.modules = [module_1, module_2]
        _db.session.add(course)
        _db.session.commit()

        first_module_responses = iter(
            [
                _FakeResponse('{"activities": [{"activityIndex": 0, "terms": []}], "videoSearchQuery": "", "videoPosition": 0}'),
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered SIMT execution and warp divergence."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(first_module_responses))
        generate_module_activities(module_1.id)

        captured_calls: list[list[dict]] = []

        def fake_completion(**kwargs):
            captured_calls.append(kwargs["messages"])
            canned = [
                '{"activities": [{"activityIndex": 0, "terms": []}], "videoSearchQuery": "", "videoPosition": 0}',
                '{"type": "reading", "title": "Memory Overview", "estimatedMinutes": 10, "body": "b"}',
                '{"digest": "Covered memory hierarchy."}',
            ]
            return _FakeResponse(canned[len(captured_calls) - 1])

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
        generate_module_activities(module_2.id)

        # First call is search planning: [system, user(data message with learning history)].
        search_plan_call = captured_calls[0]
        assert search_plan_call[0]["role"] == "system"
        assert "Covered SIMT execution and warp divergence." in search_plan_call[1]["content"]
