"""Integration tests: a malformed real LLM response should fail validation.

Unlike the rest of the course-generation tests, these run with LLM_TEST_MODE
off (so the real complete()/litellm.completion code path is exercised) but
litellm.completion itself is monkeypatched, so no network call happens and
the database is still an isolated in-memory instance.
"""

import pytest

from app.services.course_generation import approve_outline, generate_outline, start_course
from app.services.llm_schemas import LLMOutputValidationError


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_start_course_raises_when_model_returns_invalid_json(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json at all"))

    with pytest.raises(LLMOutputValidationError):
        start_course("I want to learn GPU programming")


def test_start_course_raises_when_model_omits_required_field(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse('{"question": "missing the done field"}'),
    )

    with pytest.raises(LLMOutputValidationError):
        start_course("I want to learn GPU programming")


def test_generate_outline_raises_when_model_omits_modules(real_llm_app, monkeypatch) -> None:
    # A valid InterviewStepSchema-shaped response, so start_course succeeds
    # and there's a real course to call generate_outline against.
    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse('{"done": false, "question": "a question"}'),
    )
    step = start_course("I want to learn GPU programming")

    # Now swap in an outline response missing the required "modules" field.
    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse(
            '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week"}'
        ),
    )

    with pytest.raises(LLMOutputValidationError):
        generate_outline(step.course.id)


def test_approve_outline_raises_when_compaction_response_is_malformed(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse('{"done": false, "question": "a question"}'),
    )
    step = start_course("I want to learn GPU programming")

    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse(
            '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
        ),
    )
    course = generate_outline(step.course.id)

    # Swap in a compaction response that isn't valid JSON.
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("not json at all"))

    with pytest.raises(LLMOutputValidationError):
        approve_outline(course.id)
