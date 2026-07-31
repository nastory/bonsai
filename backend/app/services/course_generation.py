"""Course-creation generation: the interview -> outline -> approve flow.

Each course carries its own ConversationMessage history from the moment
the interview starts, through outline revisions, and (eventually) into
module check-ins and direction changes, so Bonsai always has a full view
of a learner's experience with a course, not just a transcript of how it
was created.
"""

from dataclasses import dataclass
from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import Course, ConversationMessage, Module
from app.services.llm import complete
from app.services.llm_schemas import CourseModuleSchema, CourseOutlineSchema, InterviewStepSchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt

MAX_INTERVIEW_QUESTIONS = 10


class CourseNotFoundError(Exception):
    """Raised when a course-generation operation targets an unknown course id."""


@dataclass
class InterviewStep:
    """The result of asking for (or answering into) the next interview question."""

    course: Course
    done: bool
    question: str | None


def start_course(first_message: str) -> InterviewStep:
    """Start a new course from the learner's initial description of what they want to learn.

    Args:
        first_message: The learner's own words describing what they want to learn.

    Returns:
        The new course (in the 'interview' stage) plus the first follow-up question.
    """
    course = Course(
        id=str(uuid4()),
        title="New Course",
        description="",
        prerequisites=[],
        estimated_timeline="",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="interview",
    )
    db.session.add(course)
    _add_message(course.id, "user", "interview_answer", first_message)

    step = _advance_interview(course)
    db.session.commit()
    return step


def submit_interview_answer(course_id: str, answer: str) -> InterviewStep:
    """Record an interview answer and ask the next question (or signal readiness).

    Args:
        course_id: The course's id.
        answer: The learner's answer to the previous question.

    Returns:
        The updated course plus the next question, or done=True if there are enough answers.

    Raises:
        CourseNotFoundError: If no course matches course_id.
    """
    course = _get_course_or_raise(course_id)
    _add_message(course.id, "user", "interview_answer", answer)

    step = _advance_interview(course)
    db.session.commit()
    return step


def generate_outline(course_id: str) -> Course:
    """Generate and persist a course outline from the interview conversation so far.

    Args:
        course_id: The course's id.

    Returns:
        The course, now with modules and stage='outline_review'.

    Raises:
        CourseNotFoundError: If no course matches course_id.
    """
    course = _get_course_or_raise(course_id)
    outline = _generate_outline_content(course, revision_feedback=None)
    _apply_outline(course, outline)
    course.stage = "outline_review"
    db.session.commit()
    return course


def submit_outline_feedback(course_id: str, feedback: str) -> Course:
    """Regenerate the outline based on the learner's revision feedback.

    Args:
        course_id: The course's id.
        feedback: The learner's requested changes, in their own words.

    Returns:
        The course with a freshly regenerated outline.

    Raises:
        CourseNotFoundError: If no course matches course_id.
    """
    course = _get_course_or_raise(course_id)
    _add_message(course.id, "user", "outline_revision_request", feedback)

    outline = _generate_outline_content(course, revision_feedback=feedback)
    _apply_outline(course, outline)
    db.session.commit()
    return course


def approve_outline(course_id: str) -> Course:
    """Approve the current outline: the course becomes active and its first module starts.

    Args:
        course_id: The course's id.

    Returns:
        The now-active course.

    Raises:
        CourseNotFoundError: If no course matches course_id.
    """
    course = _get_course_or_raise(course_id)
    course.stage = "active"
    if course.modules:
        course.modules[0].status = "in_progress"
    _add_message(course.id, "user", "outline_approved", "Approved. Let's start learning.")
    db.session.commit()
    return course


def _get_course_or_raise(course_id: str) -> Course:
    course = db.session.get(Course, course_id)
    if course is None:
        raise CourseNotFoundError(f"No course with id '{course_id}'")
    return course


def _add_message(course_id: str, role: str, kind: str, content: str) -> None:
    db.session.add(ConversationMessage(course_id=course_id, role=role, kind=kind, content=content))


def _format_history(course: Course) -> str:
    return "\n".join(
        f"{'Learner' if m.role == 'user' else 'Bonsai'}: {m.content}" for m in course.conversation if m.content
    )


def _topic_from_conversation(course: Course) -> str:
    first_answer = next((m.content for m in course.conversation if m.kind == "interview_answer"), "")
    return first_answer or course.title


def _advance_interview(course: Course) -> InterviewStep:
    questions_asked = sum(1 for m in course.conversation if m.kind == "interview_question")
    result = _next_interview_step(course, questions_asked)

    if result.done:
        return InterviewStep(course=course, done=True, question=None)

    _add_message(course.id, "assistant", "interview_question", result.question or "")
    return InterviewStep(course=course, done=False, question=result.question)


def _next_interview_step(course: Course, questions_asked: int) -> InterviewStepSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        if questions_asked >= MAX_INTERVIEW_QUESTIONS:
            return InterviewStepSchema(done=True, question=None)
        return InterviewStepSchema(
            done=False, question=f"[MOCK] Follow-up question {questions_asked + 1} about your goals."
        )

    prompt = load_prompt(
        "course_interview",
        topic=_topic_from_conversation(course),
        questions_asked=questions_asked,
        max_questions=MAX_INTERVIEW_QUESTIONS,
        history=_format_history(course),
    )
    raw = complete(messages=[{"role": "user", "content": prompt}], **resolve_model_config())
    return validate_llm_json(raw, InterviewStepSchema)


def _generate_outline_content(course: Course, revision_feedback: str | None) -> CourseOutlineSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_outline(course, revision_feedback)

    revision_section = f"The learner asked for these changes: {revision_feedback}" if revision_feedback else ""
    prompt = load_prompt("course_outline", history=_format_history(course), revision_section=revision_section)
    raw = complete(messages=[{"role": "user", "content": prompt}], **resolve_model_config())
    return validate_llm_json(raw, CourseOutlineSchema)


def _mock_outline(course: Course, revision_feedback: str | None) -> CourseOutlineSchema:
    topic = _topic_from_conversation(course)
    suffix = " (revised)" if revision_feedback else ""
    return CourseOutlineSchema(
        title=f"{topic}{suffix}",
        description=f"A course about {topic}.",
        prerequisites=[],
        estimatedTimeline="4 weeks",
        modules=[
            CourseModuleSchema(
                title="Getting Started",
                description="Foundational concepts.",
                estimatedTimeline="1 week",
                learningOutcomes=["Understand the basics"],
            ),
            CourseModuleSchema(
                title="Going Deeper",
                description="Building on the fundamentals.",
                estimatedTimeline="2 weeks",
                learningOutcomes=["Apply core techniques"],
            ),
            CourseModuleSchema(
                title="Capstone Project",
                description="Bring it together with a final project.",
                estimatedTimeline="1 week",
                learningOutcomes=["Complete an end-to-end project"],
            ),
        ],
    )


def _apply_outline(course: Course, outline: CourseOutlineSchema) -> None:
    course.title = outline.title
    course.description = outline.description
    course.prerequisites = outline.prerequisites
    course.estimated_timeline = outline.estimatedTimeline

    course.modules = [
        Module(
            id=str(uuid4()),
            position=i,
            title=m.title,
            description=m.description,
            estimated_timeline=m.estimatedTimeline,
            status="locked",
            learning_outcomes=m.learningOutcomes,
        )
        for i, m in enumerate(outline.modules)
    ]

    _add_message(course.id, "assistant", "outline_presented", outline.model_dump_json())
