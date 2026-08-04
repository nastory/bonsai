"""Tests for LLM output schema validation.

Pins down the contract between a prompt's "respond with JSON in this shape"
instruction and what the rest of the app is willing to trust: malformed or
oddly-shaped output should fail loudly and specifically here, not surface
as a confusing KeyError deep in course_generation.py.
"""

import pytest

from app.services.llm_schemas import (
    CourseOutlineSchema,
    GeneratedActivitySchema,
    InterviewStepSchema,
    LLMOutputValidationError,
    ModuleDigestSchema,
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


def test_validate_llm_json_raises_for_empty_question_when_not_done() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"done": false, "question": ""}', InterviewStepSchema)


def test_validate_llm_json_raises_for_null_question_when_not_done() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"done": false, "question": null}', InterviewStepSchema)


def test_validate_llm_json_raises_for_whitespace_only_question_when_not_done() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"done": false, "question": "   "}', InterviewStepSchema)


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


def test_validate_llm_json_accepts_module_with_planned_activities() -> None:
    raw = """
    {
        "title": "GPU Programming", "description": "A practical intro.", "prerequisites": [],
        "estimatedTimeline": "6 weeks",
        "modules": [
            {
                "title": "Basics", "description": "d", "estimatedTimeline": "1 week", "learningOutcomes": ["Explain SIMT"],
                "plannedActivities": [
                    {"type": "reading", "title": "Intro to GPUs", "plan": "Cover the basics of GPU architecture."},
                    {"type": "assessment", "title": "Check Your Understanding", "plan": "Quiz the fundamentals."}
                ]
            }
        ]
    }
    """

    result = validate_llm_json(raw, CourseOutlineSchema)

    assert len(result.modules[0].plannedActivities) == 2
    assert result.modules[0].plannedActivities[0].type == "reading"
    assert result.modules[0].plannedActivities[1].plan == "Quiz the fundamentals."


def test_validate_llm_json_module_planned_activities_defaults_to_empty_list() -> None:
    raw = """
    {
        "title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week",
        "modules": [{"title": "M", "description": "d", "estimatedTimeline": "1 week"}]
    }
    """

    result = validate_llm_json(raw, CourseOutlineSchema)

    assert result.modules[0].plannedActivities == []


def test_validate_llm_json_raises_for_invalid_planned_activity_type() -> None:
    raw = """
    {
        "title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week",
        "modules": [
            {
                "title": "M", "description": "d", "estimatedTimeline": "1 week",
                "plannedActivities": [{"type": "video", "title": "T", "plan": "p"}]
            }
        ]
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, CourseOutlineSchema)


def test_validate_llm_json_accepts_well_formed_generated_activity() -> None:
    raw = '{"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.type == "reading"
    assert result.body == "Some reading."


def test_validate_llm_json_raises_for_invalid_activity_type() -> None:
    raw = '{"type": "video", "title": "T", "estimatedMinutes": 10}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_generated_activity_omits_type_specific_fields_when_not_given() -> None:
    raw = '{"type": "discussion", "title": "Talk", "estimatedMinutes": 10, "prompt": "Thoughts?"}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.body is None
    assert result.question is None
    assert result.prompt == "Thoughts?"


def test_validate_llm_json_accepts_activity_citations() -> None:
    raw = """
    {
        "type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading.",
        "citations": [{"label": "An Introduction to GPUs", "url": "https://example.com/gpus"}]
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.citations[0].label == "An Introduction to GPUs"
    assert result.citations[0].url == "https://example.com/gpus"


def test_validate_llm_json_activity_citations_default_to_none() -> None:
    raw = '{"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.citations is None


def test_validate_llm_json_accepts_well_formed_quiz_with_answer_and_explanation() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "question": "What is a GPU?", "options": ["A processor", "A monitor"],
        "correctAnswerIndex": 0, "explanation": "GPUs are specialized processors."
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.correctAnswerIndex == 0
    assert result.explanation == "GPUs are specialized processors."


def test_validate_llm_json_raises_when_quiz_is_missing_a_correct_answer() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "question": "What is a GPU?", "options": ["A processor", "A monitor"],
        "explanation": "GPUs are specialized processors."
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_raises_when_correct_answer_index_is_out_of_range() -> None:
    raw = """
    {
        "type": "assessment", "title": "Check", "estimatedMinutes": 10,
        "question": "What is a GPU?", "options": ["A processor", "A monitor"],
        "correctAnswerIndex": 5, "explanation": "GPUs are specialized processors."
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_raises_when_quiz_is_missing_an_explanation() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "question": "What is a GPU?", "options": ["A processor", "A monitor"],
        "correctAnswerIndex": 0
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_accepts_well_formed_module_digest() -> None:
    raw = '{"digest": "Covered SIMT execution and warp divergence."}'

    result = validate_llm_json(raw, ModuleDigestSchema)

    assert result.digest == "Covered SIMT execution and warp divergence."


def test_validate_llm_json_raises_when_module_digest_missing_digest_field() -> None:
    raw = "{}"

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, ModuleDigestSchema)
