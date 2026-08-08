"""Tests for LLM output schema validation.

Pins down the contract between a prompt's "respond with JSON in this shape"
instruction and what the rest of the app is willing to trust: malformed or
oddly-shaped output should fail loudly and specifically here, not surface
as a confusing KeyError deep in course_generation.py.
"""

import pytest

from pydantic import ValidationError

from app.services.llm_schemas import (
    AMAAnswerSchema,
    AMASearchTermsSchema,
    CourseInterviewStepSchema,
    CourseOutlineSchema,
    CourseSelectionSchema,
    DirectionChangeInterviewStepSchema,
    GeneratedActivitySchema,
    GeneratedAssessmentDecodingSchema,
    GeneratedFlashCardSetSchema,
    GeneratedQuizDecodingSchema,
    GeneratedQuizSetSchema,
    LLMOutputValidationError,
    ModuleDigestSchema,
    validate_llm_json,
)


def _question(n: int = 1) -> dict:
    return {"question": f"Q{n}", "options": ["A", "B"], "correctAnswerIndex": 0, "explanation": f"e{n}"}


def test_validate_llm_json_accepts_well_formed_course_interview_step() -> None:
    raw = '{"topicsCovered": ["experience"], "message": "What is your experience level?"}'
    result = validate_llm_json(raw, CourseInterviewStepSchema)

    assert result.topicsCovered == ["experience"]
    assert result.message == "What is your experience level?"


def test_course_interview_step_accepts_an_empty_topics_covered_list() -> None:
    result = CourseInterviewStepSchema(topicsCovered=[], message="What would you like to learn?")

    assert result.topicsCovered == []


def test_course_interview_step_rejects_an_unknown_topic() -> None:
    with pytest.raises(ValidationError):
        CourseInterviewStepSchema(topicsCovered=["not-a-real-topic"], message="hi")


def test_validate_llm_json_strips_markdown_code_fences_for_course_interview_step() -> None:
    raw = (
        '```json\n{"topicsCovered": ["experience", "motivation", "focus", "depth", "constraints"], '
        '"message": "Got it, that is enough to build your course."}\n```'
    )

    result = validate_llm_json(raw, CourseInterviewStepSchema)

    assert len(result.topicsCovered) == 5
    assert result.message == "Got it, that is enough to build your course."


def test_validate_llm_json_raises_for_invalid_json_syntax() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json("this is not json", CourseInterviewStepSchema)


def test_validate_llm_json_raises_for_missing_required_field_on_course_interview_step() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"message": "only a message, no topicsCovered field"}', CourseInterviewStepSchema)


def test_validate_llm_json_raises_for_whitespace_only_message() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json('{"topicsCovered": [], "message": "   "}', CourseInterviewStepSchema)


def test_validate_llm_json_accepts_well_formed_direction_change_interview_step() -> None:
    raw = '{"understanding": "wants more hands-on practice", "done": false, "message": "What pace works for you?"}'
    result = validate_llm_json(raw, DirectionChangeInterviewStepSchema)

    assert result.done is False
    assert result.understanding == "wants more hands-on practice"
    assert result.message == "What pace works for you?"


def test_validate_llm_json_raises_for_null_message_when_done() -> None:
    """The exact degenerate response reproduced live against Ollama/llama3: a structurally
    plausible {"done": true, "message": null} that used to pass because "question" was
    Optional. Both required fields here reject it, closing the gap at the schema level
    rather than relying solely on the model_validator below to catch it after the fact."""
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(
            '{"understanding": "all resolved", "done": true, "message": null}', DirectionChangeInterviewStepSchema
        )


def test_validate_llm_json_raises_for_blank_understanding() -> None:
    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(
            '{"understanding": "   ", "done": false, "message": "What pace works for you?"}',
            DirectionChangeInterviewStepSchema,
        )


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


def test_validate_llm_json_accepts_capstone_planned_activity() -> None:
    raw = """
    {
        "title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week",
        "modules": [
            {
                "title": "M", "description": "d", "estimatedTimeline": "1 week",
                "plannedActivities": [{"type": "capstone", "title": "Final Project", "plan": "Tie it all together."}]
            }
        ]
    }
    """

    result = validate_llm_json(raw, CourseOutlineSchema)

    assert result.modules[0].plannedActivities[0].type == "capstone"


def test_validate_llm_json_accepts_well_formed_generated_activity() -> None:
    raw = '{"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.type == "reading"
    assert result.body == "Some reading."


def test_validate_llm_json_raises_for_invalid_activity_type() -> None:
    raw = '{"type": "video", "title": "T", "estimatedMinutes": 10}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_accepts_capstone_generated_activity() -> None:
    raw = '{"type": "capstone", "title": "Capstone Project", "estimatedMinutes": 60, "prompt": "Build something real."}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.type == "capstone"
    assert result.prompt == "Build something real."


def test_validate_llm_json_generated_activity_omits_type_specific_fields_when_not_given() -> None:
    raw = '{"type": "discussion", "title": "Talk", "estimatedMinutes": 10, "prompt": "Thoughts?"}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.body is None
    assert result.questions is None
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


def test_validate_llm_json_accepts_a_readings_check_question() -> None:
    raw = """
    {
        "type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading.",
        "checkQuestion": {
            "question": "What's the key idea?", "options": ["A", "B"],
            "correctAnswerIndex": 0, "explanation": "Because A is right."
        }
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.checkQuestion.question == "What's the key idea?"
    assert result.checkQuestion.correctAnswerIndex == 0


def test_generated_activity_check_question_is_optional() -> None:
    result = GeneratedActivitySchema(type="reading", title="Intro", estimatedMinutes=15, body="Some reading.")

    assert result.checkQuestion is None


def test_generated_activity_rejects_check_question_with_out_of_bounds_correct_answer() -> None:
    with pytest.raises(ValidationError):
        GeneratedActivitySchema(
            type="reading",
            title="Intro",
            estimatedMinutes=15,
            body="Some reading.",
            checkQuestion={"question": "Q", "options": ["A", "B"], "correctAnswerIndex": 5, "explanation": "e"},
        )


def test_generated_activity_rejects_check_question_with_blank_explanation() -> None:
    with pytest.raises(ValidationError):
        GeneratedActivitySchema(
            type="reading",
            title="Intro",
            estimatedMinutes=15,
            body="Some reading.",
            checkQuestion={"question": "Q", "options": ["A", "B"], "correctAnswerIndex": 0, "explanation": "  "},
        )


def test_validate_llm_json_activity_citations_default_to_none() -> None:
    raw = '{"type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading."}'

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.citations is None


def test_validate_llm_json_accepts_a_document_citation_with_no_url() -> None:
    raw = """
    {
        "type": "reading", "title": "Intro", "estimatedMinutes": 15, "body": "Some reading.",
        "citations": [{"label": "paper.pdf, p. 4"}]
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.citations[0].label == "paper.pdf, p. 4"
    assert result.citations[0].url is None


def test_validate_llm_json_accepts_well_formed_quiz_with_answer_and_explanation() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "questions": [
            {
                "question": "What is a GPU?", "options": ["A processor", "A monitor"],
                "correctAnswerIndex": 0, "explanation": "GPUs are specialized processors."
            }
        ]
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert result.questions[0].correctAnswerIndex == 0
    assert result.questions[0].explanation == "GPUs are specialized processors."


def test_validate_llm_json_accepts_a_quiz_with_multiple_questions() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "questions": [
            {"question": "Q1", "options": ["A", "B"], "correctAnswerIndex": 0, "explanation": "e1"},
            {"question": "Q2", "options": ["A", "B"], "correctAnswerIndex": 1, "explanation": "e2"},
            {"question": "Q3", "options": ["A", "B"], "correctAnswerIndex": 0, "explanation": "e3"}
        ]
    }
    """

    result = validate_llm_json(raw, GeneratedActivitySchema)

    assert len(result.questions) == 3
    assert [q.question for q in result.questions] == ["Q1", "Q2", "Q3"]


def test_validate_llm_json_raises_when_quiz_has_no_questions() -> None:
    raw = '{"type": "quiz", "title": "Check", "estimatedMinutes": 10, "questions": []}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_raises_when_quiz_omits_questions_entirely() -> None:
    raw = '{"type": "quiz", "title": "Check", "estimatedMinutes": 10}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_raises_when_correct_answer_index_is_out_of_range() -> None:
    raw = """
    {
        "type": "assessment", "title": "Check", "estimatedMinutes": 10,
        "questions": [
            {
                "question": "What is a GPU?", "options": ["A processor", "A monitor"],
                "correctAnswerIndex": 5, "explanation": "GPUs are specialized processors."
            }
        ]
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_validate_llm_json_raises_when_one_question_among_several_is_missing_an_explanation() -> None:
    raw = """
    {
        "type": "quiz", "title": "Check", "estimatedMinutes": 10,
        "questions": [
            {"question": "Q1", "options": ["A", "B"], "correctAnswerIndex": 0, "explanation": "e1"},
            {"question": "Q2", "options": ["A", "B"], "correctAnswerIndex": 1, "explanation": ""}
        ]
    }
    """

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, GeneratedActivitySchema)


def test_quiz_decoding_schema_accepts_one_to_three_questions() -> None:
    for count in (1, 2, 3):
        GeneratedQuizDecodingSchema(
            type="quiz", title="Check", estimatedMinutes=10, questions=[_question(n) for n in range(count)]
        )


def test_quiz_decoding_schema_rejects_more_than_three_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedQuizDecodingSchema(
            type="quiz", title="Check", estimatedMinutes=10, questions=[_question(n) for n in range(4)]
        )


def test_quiz_decoding_schema_rejects_zero_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedQuizDecodingSchema(type="quiz", title="Check", estimatedMinutes=10, questions=[])


def test_assessment_decoding_schema_accepts_ten_to_fifteen_questions() -> None:
    for count in (10, 12, 15):
        GeneratedAssessmentDecodingSchema(
            type="assessment", title="Final", estimatedMinutes=30, questions=[_question(n) for n in range(count)]
        )


def test_assessment_decoding_schema_rejects_fewer_than_ten_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedAssessmentDecodingSchema(
            type="assessment", title="Final", estimatedMinutes=30, questions=[_question(n) for n in range(9)]
        )


def test_assessment_decoding_schema_rejects_more_than_fifteen_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedAssessmentDecodingSchema(
            type="assessment", title="Final", estimatedMinutes=30, questions=[_question(n) for n in range(16)]
        )


def test_validate_llm_json_accepts_well_formed_module_digest() -> None:
    raw = '{"digest": "Covered SIMT execution and warp divergence."}'

    result = validate_llm_json(raw, ModuleDigestSchema)

    assert result.digest == "Covered SIMT execution and warp divergence."


def test_validate_llm_json_raises_when_module_digest_missing_digest_field() -> None:
    raw = "{}"

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, ModuleDigestSchema)


def _flash_card(n: int = 1) -> dict:
    return {"question": f"Q{n}", "answer": f"A{n}"}


def test_flash_card_set_schema_accepts_six_to_twelve_cards() -> None:
    for count in (6, 9, 12):
        GeneratedFlashCardSetSchema(cards=[_flash_card(n) for n in range(count)])


def test_flash_card_set_schema_rejects_fewer_than_six_cards() -> None:
    with pytest.raises(ValidationError):
        GeneratedFlashCardSetSchema(cards=[_flash_card(n) for n in range(5)])


def test_flash_card_set_schema_rejects_more_than_twelve_cards() -> None:
    with pytest.raises(ValidationError):
        GeneratedFlashCardSetSchema(cards=[_flash_card(n) for n in range(13)])


def test_validate_llm_json_accepts_well_formed_flash_card_set() -> None:
    raw = """
    {
        "cards": [
            {"question": "What is a GPU?", "answer": "A specialized parallel processor."},
            {"question": "What is SIMT?", "answer": "Single Instruction, Multiple Threads."},
            {"question": "Q3", "answer": "A3"}, {"question": "Q4", "answer": "A4"},
            {"question": "Q5", "answer": "A5"}, {"question": "Q6", "answer": "A6"}
        ]
    }
    """

    result = validate_llm_json(raw, GeneratedFlashCardSetSchema)

    assert len(result.cards) == 6
    assert result.cards[0].question == "What is a GPU?"


def test_quiz_set_schema_accepts_four_to_eight_questions() -> None:
    for count in (4, 6, 8):
        GeneratedQuizSetSchema(questions=[_question(n) for n in range(count)])


def test_quiz_set_schema_rejects_fewer_than_four_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedQuizSetSchema(questions=[_question(n) for n in range(3)])


def test_quiz_set_schema_rejects_more_than_eight_questions() -> None:
    with pytest.raises(ValidationError):
        GeneratedQuizSetSchema(questions=[_question(n) for n in range(9)])


def test_search_terms_schema_accepts_one_to_three_terms() -> None:
    for count in (1, 2, 3):
        AMASearchTermsSchema(terms=[f"term {n}" for n in range(count)])


def test_search_terms_schema_rejects_zero_terms() -> None:
    with pytest.raises(ValidationError):
        AMASearchTermsSchema(terms=[])


def test_search_terms_schema_rejects_more_than_three_terms() -> None:
    with pytest.raises(ValidationError):
        AMASearchTermsSchema(terms=["a", "b", "c", "d"])


def test_validate_llm_json_accepts_well_formed_search_terms() -> None:
    raw = '{"terms": ["gpu memory coalescing", "warp scheduling"]}'

    result = validate_llm_json(raw, AMASearchTermsSchema)

    assert result.terms == ["gpu memory coalescing", "warp scheduling"]


def test_course_selection_schema_accepts_up_to_three_course_ids() -> None:
    for count in (0, 1, 3):
        CourseSelectionSchema(reasoning="thinking", courseIds=[f"c{n}" for n in range(count)])


def test_course_selection_schema_rejects_more_than_three_course_ids() -> None:
    with pytest.raises(ValidationError):
        CourseSelectionSchema(reasoning="thinking", courseIds=["c0", "c1", "c2", "c3"])


def test_validate_llm_json_accepts_empty_course_selection() -> None:
    raw = '{"reasoning": "nothing matches", "courseIds": []}'

    result = validate_llm_json(raw, CourseSelectionSchema)

    assert result.courseIds == []


def test_validate_llm_json_accepts_well_formed_ama_answer() -> None:
    raw = '{"answer": "GPUs use SIMT execution."}'

    result = validate_llm_json(raw, AMAAnswerSchema)

    assert result.answer == "GPUs use SIMT execution."


def test_validate_llm_json_raises_for_blank_ama_answer() -> None:
    raw = '{"answer": ""}'

    with pytest.raises(LLMOutputValidationError):
        validate_llm_json(raw, AMAAnswerSchema)
