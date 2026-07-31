"""Integration test: a malformed real LLM response should fail validation.

Mirrors test_course_generation_llm_validation.py's pattern: LLM_TEST_MODE
off (real_llm_app fixture) so the real complete()/validate_llm_json() path
runs, but litellm.completion is monkeypatched so no network call happens.
"""

import pytest

from app.extensions import db as _db
from app.models import Course, Module
from app.services.llm_schemas import LLMOutputValidationError
from app.services.module_generation import generate_module_activities


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _make_module() -> Module:
    course = Course(
        id="c1",
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_module_activities_raises_when_model_returns_invalid_json(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json at all"))

        with pytest.raises(LLMOutputValidationError):
            generate_module_activities(module.id)


def test_generate_module_activities_raises_when_model_omits_activities(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"notActivities": []}'),
        )

        with pytest.raises(LLMOutputValidationError):
            generate_module_activities(module.id)
