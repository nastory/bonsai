"""Tests for LLM output schema validation.

Pins down the contract between a prompt's "respond with JSON in this shape"
instruction and what the rest of the app is willing to trust: malformed or
oddly-shaped output should fail loudly and specifically here, not surface
as a confusing KeyError deep in course_generation.py.
"""

import pytest

from app.services.llm_schemas import (
    CourseOutlineSchema,
    InterviewStepSchema,
    LLMOutputValidationError,
    ModuleActivitiesSchema,
    validate_llm_json,
)


def test_validate_llm_json_accepts_well_formed_interview_step() -> None:
    result = validate_llm_json('{"done": false, "question": "What is your experience level?"}', InterviewStepSchema)

    assert result.done is False
    assert result.question == "What is your experience level?"


def test_validate_llm_json_strips_markdown_code_fences() -> None:
    raw = '```json\n{"done": true, "question": null}\n```'

    result = validate_llm_json(raw, InterviewStepSchema)

    assert result.done is True
    assert result.question is None


def test_validate_llm_json_raises_for_invalid_json_syntax() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json("this is not json", InterviewStepSchema)


def test_validate_llm_json_raises_for_missing_required_field() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"question": "only a question, no done field"}', InterviewStepSchema)


def test_validate_llm_json_raises_for_wrong_type() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"done": "not a boolean", "question": null}', InterviewStepSchema)


def test_validate_llm_json_accepts_well_formed_course_outline() -> None:
    raw = """
    {
        "title": "GPU Programming",
        "description": "A practical intro.",
        "prerequisites": ["Python"],
        "estimatedTimeline": "6 weeks",
        "modules": [
            {"title": "Basics", "description": "d", "estimatedTimeline": "1 week", "learningOutcomes": ["Explain SIMT"]}
        ]
    }
    """

    result = validate_llm_json(raw, CourseOutlineSchema)

    assert result.title == "GPU Programming"
    assert len(result.modules) == 1
    assert result.modules[0].title == "Basics"


def test_validate_llm_json_raises_when_modules_missing() -> None:
    raw = '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week"}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, CourseOutlineSchema)


def test_validate_llm_json_raises_when_module_missing_required_field() -> None:
    raw = """
    {
        "title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week",
        "modules": [{"title": "Missing description and timeline"}]
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, CourseOutlineSchema)


def test_validate_llm_json_accepts_well_formed_module_activities() -> None:
    raw = """
    {
        "activities": [
            {"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."},
            {"type": "quiz", "title": "Check", "estimatedMinutes": 5, "question": "Why?", "options": ["A", "B"]}
        ]
    }
    """

    result = validate_llm_json(raw, ModuleActivitiesSchema)

    assert len(result.activities) == 2
    assert result.activities[0].type == "reading"
    assert result.activities[0].body == "Some reading."
    assert result.activities[1].options == ["A", "B"]


def test_validate_llm_json_raises_for_invalid_activity_type() -> None:
    raw = '{"activities": [{"type": "video", "title": "T", "estimatedMinutes": 10}]}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, ModuleActivitiesSchema)


def test_validate_llm_json_module_activities_omits_type_specific_fields_when_not_given() -> None:
    raw = '{"activities": [{"type": "discussion", "title": "Talk", "estimatedMinutes": 10, "prompt": "Thoughts?"}]}'

    result = validate_llm_json(raw, ModuleActivitiesSchema)

    assert result.activities[0].body is None
    assert result.activities[0].question is None
    assert result.activities[0].prompt == "Thoughts?"


def test_validate_llm_json_accepts_activity_citations() -> None:
    raw = """
    {
        "activities": [
            {
                "type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading.",
                "citations": [{"label": "An Introduction to GPUs", "url": "https://example.com/gpus"}]
            }
        ]
    }
    """

    result = validate_llm_json(raw, ModuleActivitiesSchema)

    assert result.activities[0].citations[0].label == "An Introduction to GPUs"
    assert result.activities[0].citations[0].url == "https://example.com/gpus"


def test_validate_llm_json_activity_citations_default_to_none() -> None:
    raw = '{"activities": [{"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."}]}'

    result = validate_llm_json(raw, ModuleActivitiesSchema)

    assert result.activities[0].citations is None
