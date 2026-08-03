"""Tests for the course-creation generation service (interview -> outline -> approve).

Runs entirely in LLM_TEST_MODE (via the `db`/`app` fixtures), so these
exercise the real control flow (question counting, stage transitions,
module creation) against deterministic canned generation output rather
than a real model.
"""

from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import ConversationMessage
from app.services.course_generation import (
    MAX_INTERVIEW_QUESTIONS,
    CourseNotFoundError,
    approve_outline,
    generate_outline,
    start_course,
    submit_interview_answer,
    submit_outline_feedback,
)
from app.services.document_extraction import DocumentExtractionError


def test_start_course_creates_course_in_interview_stage(db) -> None:
    step = start_course("I want to learn GPU programming")

    assert step.course.stage == "interview"
    assert step.done is False
    assert step.question is not None


def test_start_course_records_the_first_message(db) -> None:
    step = start_course("I want to learn GPU programming")

    contents = [m.content for m in step.course.conversation]
    assert "I want to learn GPU programming" in contents


def test_start_course_with_a_file_persists_a_source_material(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert len(step.course.source_materials) == 1
    assert step.course.source_materials[0].file_name == "notes.txt"


def test_start_course_with_a_file_computes_an_interview_summary(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert step.course.source_materials[0].interview_summary == "[MOCK] Summary of the document."


def test_start_course_with_an_unparseable_file_persists_nothing(db) -> None:
    file = FileStorage(stream=BytesIO(b"not a real docx"), filename="notes.docx")

    with pytest.raises(DocumentExtractionError):
        start_course("I want to learn about this paper", files=[file])


def test_submit_interview_answer_with_a_file_persists_a_source_material(db) -> None:
    step = start_course("I want to learn GPU programming")
    file = FileStorage(stream=BytesIO(b"Efficient memory coalescing in CUDA kernels."), filename="paper.txt")

    step2 = submit_interview_answer(step.course.id, "here's a paper", files=[file])

    assert len(step2.course.source_materials) == 1
    assert step2.course.source_materials[0].file_name == "paper.txt"


def test_interview_question_reflects_an_attached_source_material(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert "notes.txt" in (step.question or "")


def test_interview_question_is_generic_without_a_source_material(db) -> None:
    step = start_course("I want to learn GPU programming")

    assert "notes.txt" not in (step.question or "")


def test_submit_interview_answer_asks_another_question(db) -> None:
    step = start_course("I want to learn GPU programming")

    step2 = submit_interview_answer(step.course.id, "I'm a beginner")

    assert step2.done is False
    assert step2.question is not None
    assert step2.question != step.question


def test_submit_interview_answer_raises_for_unknown_course(db) -> None:
    with pytest.raises(CourseNotFoundError):
        submit_interview_answer("does-not-exist", "answer")


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_interview_prompt_uses_document_summary_not_raw_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        # start_course() with a file makes two real calls in order: summarize
        # the document (ingestion), then ask the first interview question.
        responses = [
            _FakeResponse('{"summary": "A short paper about GPU memory coalescing."}'),
            _FakeResponse('{"done": false, "question": "a question"}'),
        ]
        captured: dict = {}

        def fake_completion(**kwargs):
            response = responses.pop(0)
            if not responses:
                captured["prompt"] = kwargs["messages"][0]["content"]
            return response

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
        file = FileStorage(
            stream=BytesIO(b"GPU memory coalescing is a key optimization technique."), filename="notes.txt"
        )

        start_course("I want to learn about this paper", files=[file])

        assert "notes.txt" in captured["prompt"]
        assert "A short paper about GPU memory coalescing." in captured["prompt"]
        assert "GPU memory coalescing is a key optimization technique." not in captured["prompt"]


def test_interview_sends_real_conversation_turns_not_flattened_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        responses = iter(
            [
                _FakeResponse('{"done": false, "question": "What is your experience with GPUs?"}'),
                _FakeResponse('{"done": false, "question": "another question"}'),
            ]
        )
        captured: list = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return next(responses)

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        step = start_course("I want to learn GPU programming")
        submit_interview_answer(step.course.id, "I'm a total beginner")

        second_call_messages = captured[1]
        assert second_call_messages[0]["role"] == "system"
        assert "${" not in second_call_messages[0]["content"]
        assert second_call_messages[1] == {"role": "user", "content": "I want to learn GPU programming"}
        assert second_call_messages[2] == {"role": "assistant", "content": "What is your experience with GPUs?"}
        assert second_call_messages[3] == {"role": "user", "content": "I'm a total beginner"}


def test_outline_prompt_includes_source_material_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        responses = [
            _FakeResponse('{"summary": "A short paper about GPU memory coalescing."}'),
            _FakeResponse('{"done": false, "question": "a question"}'),
        ]
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: responses.pop(0))
        file = FileStorage(
            stream=BytesIO(b"GPU memory coalescing is a key optimization technique."), filename="notes.txt"
        )
        step = start_course("I want to learn about this paper", files=[file])

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse(
                '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_outline(step.course.id)

        assert "notes.txt" in captured["prompt"]
        assert "GPU memory coalescing is a key optimization technique." in captured["prompt"]


def test_outline_regeneration_includes_prior_outline_and_revision_request_as_turns(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        responses = [
            _FakeResponse('{"done": false, "question": "a question"}'),
            _FakeResponse(
                '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            ),
        ]
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: responses.pop(0))
        step = start_course("I want to learn GPU programming")
        generate_outline(step.course.id)

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse(
                '{"title": "T2", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        submit_outline_feedback(step.course.id, "Make it shorter")

        roles = [m["role"] for m in captured["messages"]]
        contents = [m["content"] for m in captured["messages"]]
        assert roles[0] == "system"
        assert "I want to learn GPU programming" in contents
        assert any('"title":"T"' in c for c in contents)  # the previously presented outline, as a turn
        assert "Make it shorter" in contents


def test_interview_stops_after_max_questions(db) -> None:
    step = start_course("I want to learn GPU programming")
    course_id = step.course.id

    for _ in range(MAX_INTERVIEW_QUESTIONS):
        step = submit_interview_answer(course_id, "some answer")

    assert step.done is True
    assert step.question is None


def test_interview_hard_stops_at_max_questions_without_calling_the_model(real_llm_app, monkeypatch) -> None:
    """The max-question cap is enforced in code, not just left to the prompt's instruction."""
    with real_llm_app.app_context():
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"done": false, "question": "a question"}'),
        )
        step = start_course("I want to learn GPU programming")
        course_id = step.course.id

        for i in range(MAX_INTERVIEW_QUESTIONS - 1):
            db.session.add(
                ConversationMessage(
                    course_id=course_id, role="assistant", kind="interview_question", content=f"q{i}"
                )
            )
        db.session.commit()

        def fail_if_called(**kwargs):
            raise AssertionError("the model should not be called once the max question count is reached")

        monkeypatch.setattr("app.services.llm.litellm.completion", fail_if_called)

        step = submit_interview_answer(course_id, "final answer")

        assert step.done is True
        assert step.question is None


def test_generate_outline_creates_modules_and_moves_to_outline_review(db) -> None:
    step = start_course("I want to learn GPU programming")

    course = generate_outline(step.course.id)

    assert course.stage == "outline_review"
    assert len(course.modules) > 0
    assert course.title != "New Course"
    assert all(m.status == "locked" for m in course.modules)


def test_generate_outline_populates_each_module_activity_plan(db) -> None:
    step = start_course("I want to learn GPU programming")

    course = generate_outline(step.course.id)

    assert all(len(m.activity_plan) > 0 for m in course.modules)
    first_activity = course.modules[0].activity_plan[0]
    assert set(first_activity) == {"type", "title", "plan"}


def test_submit_outline_feedback_regenerates_modules(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)
    original_title = course.title

    revised = submit_outline_feedback(course.id, "add more on memory management")

    assert revised.title != original_title
    assert any(m.kind == "outline_revision_request" for m in revised.conversation)


def test_approve_outline_activates_course_and_starts_first_module(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.stage == "active"
    assert approved.modules[0].status == "in_progress"


def test_approve_outline_compacts_and_stores_course_context(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.context_summary is not None
    assert approved.context_summary["summary"]
    assert approved.context_summary["learnerProfile"]
    assert approved.context_summary["keyDecisions"] == []
