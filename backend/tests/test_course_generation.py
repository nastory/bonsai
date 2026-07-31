"""Tests for the course-creation generation service (interview -> outline -> approve).

Runs entirely in LLM_TEST_MODE (via the `db`/`app` fixtures), so these
exercise the real control flow (question counting, stage transitions,
module creation) against deterministic canned generation output rather
than a real model.
"""

import pytest

from app.services.course_generation import (
    MAX_INTERVIEW_QUESTIONS,
    CourseNotFoundError,
    approve_outline,
    generate_outline,
    start_course,
    submit_interview_answer,
    submit_outline_feedback,
)


def test_start_course_creates_course_in_interview_stage(db) -> None:
    step = start_course("I want to learn GPU programming")

    assert step.course.stage == "interview"
    assert step.done is False
    assert step.question is not None


def test_start_course_records_the_first_message(db) -> None:
    step = start_course("I want to learn GPU programming")

    contents = [m.content for m in step.course.conversation]
    assert "I want to learn GPU programming" in contents


def test_submit_interview_answer_asks_another_question(db) -> None:
    step = start_course("I want to learn GPU programming")

    step2 = submit_interview_answer(step.course.id, "I'm a beginner")

    assert step2.done is False
    assert step2.question is not None
    assert step2.question != step.question


def test_submit_interview_answer_raises_for_unknown_course(db) -> None:
    with pytest.raises(CourseNotFoundError):
        submit_interview_answer("does-not-exist", "answer")


def test_interview_stops_after_max_questions(db) -> None:
    step = start_course("I want to learn GPU programming")
    course_id = step.course.id

    for _ in range(MAX_INTERVIEW_QUESTIONS):
        step = submit_interview_answer(course_id, "some answer")

    assert step.done is True
    assert step.question is None


def test_generate_outline_creates_modules_and_moves_to_outline_review(db) -> None:
    step = start_course("I want to learn GPU programming")

    course = generate_outline(step.course.id)

    assert course.stage == "outline_review"
    assert len(course.modules) > 0
    assert course.title != "New Course"
    assert all(m.status == "locked" for m in course.modules)


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
