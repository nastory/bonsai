"""Course lifecycle: the interview -> outline -> approve creation flow, and deletion.

Each course carries its own ConversationMessage history from the moment
the interview starts, through outline revisions, and (eventually) into
module check-ins and direction changes, so Bonsai always has a full view
of a learner's experience with a course, not just a transcript of how it
was created.
"""

from dataclasses import dataclass
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import Course, ConversationMessage, Module, SourceMaterial
from app.services.course_context import (
    compact_course_context,
    conversation_turns,
    render_source_materials,
    render_source_material_summaries,
    summarize_document_for_interview,
)
from app.services.document_extraction import extract_text
from app.services.llm import complete
from app.services.llm_schemas import (
    CourseModuleSchema,
    CourseOutlineSchema,
    InterviewStepSchema,
    PlannedActivitySchema,
    validate_llm_json,
)
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt
from app.services.content_storage import delete_activity_content
from app.services.source_material_storage import delete_source_material_text, save_source_material_text

MAX_INTERVIEW_QUESTIONS = 10


class CourseNotFoundError(Exception):
    """Raised when a course-generation operation targets an unknown course id."""


@dataclass
class InterviewStep:
    """The result of asking for (or answering into) the next interview question."""

    course: Course
    done: bool
    question: str | None


def start_course(first_message: str, files: list[FileStorage] | None = None) -> InterviewStep:
    """Start a new course from the learner's initial description of what they want to learn.

    Args:
        first_message: The learner's own words describing what they want to learn.
        files: Any documents attached alongside the first message. Ingested
            before the first follow-up question is asked, so that question
            can already be shaped by the document (see _ingest_source_materials).

    Returns:
        The new course (in the 'interview' stage) plus the first follow-up question.

    Raises:
        DocumentExtractionError: If an attached file can't be parsed. Nothing
            about this call is persisted in that case (see _ingest_source_materials).
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
    # Ingest before anything is added to the session: resolve_model_config()
    # (called for summarization, if there are files) can trigger its own
    # commit on first use (UserSettings.get_or_create()), which would
    # otherwise prematurely persist this course/message if extraction then
    # failed on a later file.
    _ingest_source_materials(course, files)
    db.session.add(course)
    _add_message(course.id, "user", "interview_answer", first_message)

    step = _advance_interview(course)
    db.session.commit()
    return step


def submit_interview_answer(
    course_id: str, answer: str, files: list[FileStorage] | None = None
) -> InterviewStep:
    """Record an interview answer and ask the next question (or signal readiness).

    Args:
        course_id: The course's id.
        answer: The learner's answer to the previous question.
        files: Any documents attached alongside this answer (a learner can
            attach a document mid-interview, not just with the first message).

    Returns:
        The updated course plus the next question, or done=True if there are enough answers.

    Raises:
        CourseNotFoundError: If no course matches course_id.
        DocumentExtractionError: If an attached file can't be parsed.
    """
    course = _get_course_or_raise(course_id)
    # Ingest before adding the answer message, for the same reason as
    # start_course(): a nested commit inside resolve_model_config() shouldn't
    # prematurely persist it if extraction then fails on a later file.
    _ingest_source_materials(course, files)
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

    Also compacts the interview + approved outline into a persistent
    Course.context_summary, so it exists before any module generation call
    can ever run (see app/services/course_context.py).

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
    context = compact_course_context(course)
    course.context_summary = context.model_dump()
    db.session.commit()
    return course


def delete_course(course_id: str) -> None:
    """Permanently delete a course and everything associated with it.

    Deletes on-disk content first (each activity's generated content, each
    source material's extracted text): SQLAlchemy's cascade="all, delete-orphan"
    on Course.modules/source_materials/conversation cleans up the DB rows,
    but has no idea these files on disk exist, so they'd otherwise be
    orphaned. Order doesn't matter for correctness (the DB delete doesn't
    depend on the files being gone first), but doing it first means a
    mid-delete crash leaves an intact course rather than a DB row pointing
    at already-deleted files.

    Args:
        course_id: The course's id.

    Raises:
        CourseNotFoundError: If no course matches course_id.
    """
    course = _get_course_or_raise(course_id)
    for module in course.modules:
        for activity in module.activities:
            if activity.content_path:
                delete_activity_content(activity.content_path)
    for material in course.source_materials:
        delete_source_material_text(material.text_path)
    db.session.delete(course)
    db.session.commit()


def _get_course_or_raise(course_id: str) -> Course:
    course = db.session.get(Course, course_id)
    if course is None:
        raise CourseNotFoundError(f"No course with id '{course_id}'")
    return course


def _add_message(course_id: str, role: str, kind: str, content: str) -> None:
    db.session.add(ConversationMessage(course_id=course_id, role=role, kind=kind, content=content))


def _ingest_source_materials(course: Course, files: list[FileStorage] | None) -> None:
    """Extract, summarize, and persist text for any documents attached to this interview turn.

    Writes each file's extracted text to disk and adds a SourceMaterial row
    to the session, but doesn't itself commit: if extraction raises partway
    through (e.g. an unsupported or corrupt file), nothing from this call —
    not the course, not the interview-answer message, not any file already
    processed in this same call — ends up persisted, since the caller's
    single db.session.commit() never runs. resolve_model_config() can
    trigger its own nested commit on first use (UserSettings.get_or_create()),
    which is why callers must call this before adding the course/message to
    the session themselves, not after.

    Args:
        course: The course these materials belong to.
        files: The uploaded files, or None/empty if none were attached.

    Raises:
        DocumentExtractionError: If a file's text can't be extracted.
    """
    files = [f for f in (files or []) if f and f.filename]
    if not files:
        return

    model_config = resolve_model_config()
    for file_storage in files:
        text = extract_text(file_storage.filename, file_storage.read())
        source_material = SourceMaterial(id=str(uuid4()), file_name=file_storage.filename, text_path="")
        source_material.text_path = save_source_material_text(source_material.id, text)
        source_material.interview_summary = summarize_document_for_interview(text, model_config)
        # Appending to the relationship (not db.session.add() + setting
        # course_id by hand) is what keeps course.source_materials correct
        # in-memory for the rest of this call — _advance_interview() reads
        # it immediately after to shape the next question, before anything
        # here is committed or reloaded from the database.
        course.source_materials.append(source_material)


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
    if questions_asked >= MAX_INTERVIEW_QUESTIONS:
        return InterviewStepSchema(done=True, question=None)

    if current_app.config.get("LLM_TEST_MODE"):
        if course.source_materials:
            filenames = ", ".join(m.file_name for m in course.source_materials)
            return InterviewStepSchema(
                done=False,
                question=f"[MOCK] Follow-up question {questions_asked + 1} about {filenames}.",
            )
        return InterviewStepSchema(
            done=False, question=f"[MOCK] Follow-up question {questions_asked + 1} about your goals."
        )

    system_prompt = load_prompt(
        "course_interview",
        questions_asked=questions_asked,
        max_questions=MAX_INTERVIEW_QUESTIONS,
        source_materials=render_source_material_summaries(course),
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course, {"interview_answer", "interview_question"}
    )
    raw = complete(messages=messages, schema=InterviewStepSchema, **resolve_model_config())
    return validate_llm_json(raw, InterviewStepSchema)


def _generate_outline_content(course: Course, revision_feedback: str | None) -> CourseOutlineSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_outline(course, revision_feedback)

    system_prompt = load_prompt("course_outline", source_materials=render_source_materials(course))
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course, {"interview_answer", "interview_question", "outline_revision_request", "outline_presented"}
    )
    raw = complete(messages=messages, schema=CourseOutlineSchema, **resolve_model_config())
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
                plannedActivities=[
                    PlannedActivitySchema(
                        type="reading", title="[MOCK] Introduction", plan="[MOCK] Cover the fundamentals."
                    ),
                    PlannedActivitySchema(
                        type="assessment", title="[MOCK] Check Your Understanding", plan="[MOCK] Quiz the basics."
                    ),
                ],
            ),
            CourseModuleSchema(
                title="Going Deeper",
                description="Building on the fundamentals.",
                estimatedTimeline="2 weeks",
                learningOutcomes=["Apply core techniques"],
                plannedActivities=[
                    PlannedActivitySchema(
                        type="reading", title="[MOCK] Core Techniques", plan="[MOCK] Cover the core techniques."
                    ),
                    PlannedActivitySchema(
                        type="discussion", title="[MOCK] Reflect and Discuss", plan="[MOCK] Discuss applications."
                    ),
                    PlannedActivitySchema(
                        type="assessment", title="[MOCK] Check Your Understanding", plan="[MOCK] Quiz the techniques."
                    ),
                ],
            ),
            CourseModuleSchema(
                title="Capstone Project",
                description="Bring it together with a final project.",
                estimatedTimeline="1 week",
                learningOutcomes=["Complete an end-to-end project"],
                plannedActivities=[
                    PlannedActivitySchema(
                        type="project", title="[MOCK] Capstone Project", plan="[MOCK] Build an end-to-end project."
                    ),
                ],
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
            activity_plan=[a.model_dump() for a in m.plannedActivities],
        )
        for i, m in enumerate(outline.modules)
    ]

    _add_message(course.id, "assistant", "outline_presented", outline.model_dump_json())
