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
from app.models import Course, ConversationMessage, LLMUsageLog, Module, SourceMaterial, UserSettings
from app.services.course_context import (
    assemble_learning_history,
    compact_course_context,
    conversation_turns,
    render_source_material_summaries,
    summarize_document_for_interview,
)
from app.services.document_chunking import chunk_pages
from app.services.document_extraction import extract_pages, extract_text
from app.services.image_generation import ImageGenerationError, generate_thumbnail_image
from app.services.llm import complete
from app.services.llm_schemas import (
    CourseDirectionChangeSchema,
    CourseModuleSchema,
    CourseOutlineSchema,
    InterviewStepSchema,
    PlannedActivitySchema,
    validate_llm_json,
)
from app.services.model_selection import (
    ImageGenerationNotConfiguredError,
    resolve_embedding_config,
    resolve_image_generation_config,
    resolve_model_config,
)
from app.services.module_generation import ModuleNotFoundError
from app.services.prompts import load_prompt
from app.services.content_storage import delete_activity_content
from app.services.source_material_storage import delete_source_material_text, save_source_material_text
from app.services.thumbnail_storage import delete_thumbnail_image, save_thumbnail_image
from app.services.vector_store import build_or_update_index, delete_vector_index

MAX_INTERVIEW_QUESTIONS = 7


class CourseNotFoundError(Exception):
    """Raised when a course-generation operation targets an unknown course id."""


@dataclass
class InterviewStep:
    """The result of asking for (or answering into) the next interview question."""

    course: Course
    done: bool
    question: str | None


def start_course(
    first_message: str,
    files: list[FileStorage] | None = None,
    parent_course_id: str | None = None,
    supplement_with_web_search: bool = False,
) -> InterviewStep:
    """Start a new course from the learner's initial description of what they want to learn.

    Args:
        first_message: The learner's own words describing what they want to learn.
        files: Any documents attached alongside the first message. Ingested
            before the first follow-up question is asked, so that question
            can already be shaped by the document (see _ingest_source_materials).
        parent_course_id: When given, this is a "Branch Off" mid-course:
            the new course's interview/outline are shaped by what the
            learner already covered in the parent course (see
            _parent_context()), and Course.parent_course_id records the
            lineage. The parent course itself is never modified — branching
            off leaves it and its own remaining modules exactly as they were.
        supplement_with_web_search: If true and files are attached, module
            generation will also search the web to supplement the document(s)
            rather than grounding solely in them - see _ingest_source_materials().
            Ignored when no files are attached in this call.

    Returns:
        The new course (in the 'interview' stage) plus the first follow-up question.

    Raises:
        CourseNotFoundError: If parent_course_id doesn't match a real course.
        DocumentExtractionError: If an attached file can't be parsed. Nothing
            about this call is persisted in that case (see _ingest_source_materials).
    """
    if parent_course_id is not None:
        _get_course_or_raise(parent_course_id)  # validate before anything else is touched

    course = Course(
        id=str(uuid4()),
        title="New Course",
        description="",
        prerequisites=[],
        estimated_timeline="",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="interview",
        parent_course_id=parent_course_id,
    )
    # Ingest before anything is added to the session: resolve_model_config()
    # (called for summarization, if there are files) can trigger its own
    # commit on first use (UserSettings.get_or_create()), which would
    # otherwise prematurely persist this course/message if extraction then
    # failed on a later file.
    _ingest_source_materials(course, files, supplement_with_web_search)
    db.session.add(course)
    _add_message(course.id, "user", "interview_answer", first_message)

    step = _advance_interview(course)
    db.session.commit()
    return step


def submit_interview_answer(
    course_id: str, answer: str, files: list[FileStorage] | None = None, supplement_with_web_search: bool = False
) -> InterviewStep:
    """Record an interview answer and ask the next question (or signal readiness).

    Args:
        course_id: The course's id.
        answer: The learner's answer to the previous question.
        files: Any documents attached alongside this answer (a learner can
            attach a document mid-interview, not just with the first message).
        supplement_with_web_search: See start_course()'s matching arg. Only
            meaningful when files are attached in this same call.

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
    _ingest_source_materials(course, files, supplement_with_web_search)
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
    _generate_thumbnail_if_enabled(course)
    db.session.commit()
    return course


def _generate_thumbnail_if_enabled(course: Course) -> None:
    """Best-effort: generate and attach a real thumbnail image, if configured.

    Never raises - an unconfigured or failing image generation model should
    never block outline approval, the same "don't let an optional
    enhancement break the core flow" precedent as module generation's
    silently-skipped visual aids. A course whose thumbnail generation is
    skipped or fails just keeps its gradient thumbnail_url fallback, same
    as every course gets by default today.

    Args:
        course: The course to generate a thumbnail for. Must already have
            a real title/description (i.e. called after outline approval,
            not at course creation, when both are still placeholders).
    """
    settings = UserSettings.get_or_create()
    if not settings.thumbnail_generation_enabled:
        return
    try:
        model_config = resolve_image_generation_config()
        prompt = f"A course thumbnail image for a course titled '{course.title}': {course.description}"
        image_bytes = generate_thumbnail_image(prompt, model_config)
        course.thumbnail_image_path = save_thumbnail_image(course.id, image_bytes)
    except (ImageGenerationNotConfiguredError, ImageGenerationError):
        current_app.logger.info("Skipping thumbnail generation for course %s: not configured or failed.", course.id)


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
    if course.vector_index_path:
        delete_vector_index(course.vector_index_path)
    if course.thumbnail_image_path:
        delete_thumbnail_image(course.thumbnail_image_path)
    db.session.delete(course)
    db.session.commit()


def reset_all_data() -> None:
    """Permanently delete every course and all learner data, and reset Settings to defaults.

    A full factory reset, not a filtered one, unlike import_data() (which
    restores courses/progress but explicitly leaves this installation's own
    API keys untouched - see data_export.py): every course is deleted (see
    delete_course() - cascades to its modules/activities/source materials/
    conversation messages/flash card sets/quiz sets, plus their on-disk
    content, vector index, and thumbnail), every LLMUsageLog row is
    cleared, and the single UserSettings row - including API keys - is
    replaced with a fresh default one. onboarding_completed reverts to its
    model default (False), so the first-time onboarding modal reappears on
    next load, the same as a genuinely fresh install.

    Irreversible - no undo. The caller (the route) is responsible for
    requiring real confirmation before calling this.
    """
    course_ids = [c.id for c in db.session.execute(db.select(Course)).scalars()]
    for course_id in course_ids:
        delete_course(course_id)

    # Bulk delete, not a per-row loop: usage logs can accumulate into the
    # thousands over normal use, and there's nothing per-row to clean up
    # (no on-disk file, no cascade) the way a course has.
    db.session.execute(db.delete(LLMUsageLog))

    db.session.delete(UserSettings.get_or_create())
    db.session.commit()
    # Recreates the single row immediately (defaults only, including a
    # fresh id=1) rather than leaving it to whatever request happens to
    # call get_or_create() next - every other part of this app assumes
    # that row always exists.
    UserSettings.get_or_create()


def start_direction_change(module_id: str, message: str) -> InterviewStep:
    """Start the "Change This Course" mid-course check-in interview for a module.

    Mirrors start_course()'s shape, scoped to a module (whose course is
    already active) instead of a fresh course. Nothing about the course's
    remaining modules is touched until approve_direction_change() commits a
    reviewed, approved proposal — this call and every other one in this
    interview/proposal flow are purely additive (new ConversationMessage
    rows tagged with this module_id).

    Args:
        module_id: The just-completed module's id, from the check-in that
            triggered this.
        message: The learner's own words about what they want different.

    Returns:
        done=False and the first check-in question (this interview always
        has at least one question worth asking, unlike the from-scratch
        interview, so this never comes back done on the first message).

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    _add_message(module.course_id, "user", "direction_interview_answer", message, module_id=module.id)
    step = _advance_direction_interview(module)
    db.session.commit()
    return step


def submit_direction_change_answer(module_id: str, answer: str) -> InterviewStep:
    """Record an answer in the "Change This Course" check-in interview and ask the next question.

    Args:
        module_id: The module's id.
        answer: The learner's answer to the previous question.

    Returns:
        The next question, or done=True once there's enough to propose new modules.

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    _add_message(module.course_id, "user", "direction_interview_answer", answer, module_id=module.id)
    step = _advance_direction_interview(module)
    db.session.commit()
    return step


def generate_direction_change_outline(module_id: str) -> CourseDirectionChangeSchema:
    """Propose a new set of modules to replace what's ahead, from the check-in interview so far.

    Nothing is applied yet: the proposal is only recorded to the
    conversation (for submit_direction_change_feedback()/approve_direction_change()
    to read back), not turned into real Module rows. Mirrors
    generate_outline(), except course creation applies its outline
    immediately (stage='outline_review' already gates it from being "live"
    for a course that doesn't exist as far as the learner's other courses
    are concerned) — an already-active course has no equivalent safe
    "reviewing" state to sit in, so this holds the proposal as data instead.

    Args:
        module_id: The module's id.

    Returns:
        The proposed modules.

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    proposal = _generate_direction_change_content(module, revision_feedback=None)
    _add_message(
        module.course_id, "assistant", "direction_outline_presented", proposal.model_dump_json(), module_id=module.id
    )
    db.session.commit()
    return proposal


def submit_direction_change_feedback(module_id: str, feedback: str) -> CourseDirectionChangeSchema:
    """Regenerate the proposed modules based on the learner's revision feedback.

    Args:
        module_id: The module's id.
        feedback: The learner's requested changes, in their own words.

    Returns:
        The revised proposed modules.

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    _add_message(module.course_id, "user", "direction_outline_revision_request", feedback, module_id=module.id)
    proposal = _generate_direction_change_content(module, revision_feedback=feedback)
    _add_message(
        module.course_id, "assistant", "direction_outline_presented", proposal.model_dump_json(), module_id=module.id
    )
    db.session.commit()
    return proposal


def approve_direction_change(module_id: str) -> Course:
    """Commit the most recently proposed modules, replacing everything ahead of this module.

    Deletes every module with position > this module's position (cascades
    to their Activity rows too, though there shouldn't be any yet — module
    generation is lazy, so nothing after the just-completed module has been
    reached, hence nothing's been generated for it), then creates new
    modules from the approved proposal at continuing positions. The first
    new module unlocks immediately (status="in_progress"), matching
    activities.py's existing unlock-cascade convention; the rest stay
    "locked". Everything at or before this module (completed modules, their
    activities, this module itself) is untouched.

    Args:
        module_id: The module's id.

    Returns:
        The course, with its remaining modules replaced.

    Raises:
        ModuleNotFoundError: If no module matches module_id, or if there's
            no proposal to approve (generate_direction_change_outline()
            hasn't been called, or nothing was ever proposed).
    """
    module = _get_module_or_raise(module_id)
    course = module.course

    proposal_message = next(
        (
            m
            for m in reversed(course.conversation)
            if m.kind == "direction_outline_presented" and m.module_id == module.id
        ),
        None,
    )
    if proposal_message is None:
        raise ModuleNotFoundError(f"No proposed direction-change outline exists for module '{module_id}'")
    proposal = CourseDirectionChangeSchema.model_validate_json(proposal_message.content)

    for stale_module in [m for m in course.modules if m.position > module.position]:
        db.session.delete(stale_module)

    for i, planned_module in enumerate(proposal.modules):
        course.modules.append(
            Module(
                id=str(uuid4()),
                position=module.position + 1 + i,
                title=planned_module.title,
                description=planned_module.description,
                estimated_timeline=planned_module.estimatedTimeline,
                status="in_progress" if i == 0 else "locked",
                learning_outcomes=planned_module.learningOutcomes,
                activity_plan=[a.model_dump() for a in planned_module.plannedActivities],
            )
        )

    _add_message(course.id, "user", "direction_change_approved", "Approved. Let's continue.", module_id=module.id)
    db.session.commit()
    return course


def _advance_direction_interview(module: Module) -> InterviewStep:
    questions_asked = sum(
        1
        for m in module.course.conversation
        if m.kind == "direction_interview_question" and m.module_id == module.id
    )
    result = _next_direction_interview_step(module, questions_asked)

    if result.done:
        return InterviewStep(course=module.course, done=True, question=None)

    _add_message(
        module.course_id, "assistant", "direction_interview_question", result.question or "", module_id=module.id
    )
    return InterviewStep(course=module.course, done=False, question=result.question)


def _next_direction_interview_step(module: Module, questions_asked: int) -> InterviewStepSchema:
    if questions_asked >= MAX_INTERVIEW_QUESTIONS:
        return InterviewStepSchema(coverage="max questions reached", done=True, question="(interview complete)")

    if current_app.config.get("LLM_TEST_MODE"):
        return InterviewStepSchema(
            coverage="[MOCK] coverage note",
            done=False,
            question=f"[MOCK] Direction-change follow-up {questions_asked + 1}.",
        )

    system_prompt = load_prompt(
        "module_direction_interview",
        questions_asked=questions_asked,
        max_questions=MAX_INTERVIEW_QUESTIONS,
        history=assemble_learning_history(module.course, up_to_module_position=module.position),
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        module.course,
        {"direction_interview_answer", "direction_interview_question"},
        module_id=module.id,
    )
    raw = complete(
        messages=messages,
        schema=InterviewStepSchema,
        course_id=module.course_id,
        module_id=module.id,
        call_type="direction_interview_question",
        **resolve_model_config(),
    )
    return validate_llm_json(raw, InterviewStepSchema)


def _generate_direction_change_content(
    module: Module, revision_feedback: str | None
) -> CourseDirectionChangeSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_direction_change(module, revision_feedback)

    system_prompt = load_prompt(
        "module_direction_outline",
        history=assemble_learning_history(module.course, up_to_module_position=module.position),
        activity_usage=_activity_type_usage_summary(module.course, up_to_module_position=module.position),
        activity_type_reference=load_prompt("activity_type_reference"),
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        module.course,
        {
            "direction_interview_answer",
            "direction_interview_question",
            "direction_outline_revision_request",
            "direction_outline_presented",
        },
        module_id=module.id,
    )
    raw = complete(
        messages=messages,
        schema=CourseDirectionChangeSchema,
        course_id=module.course_id,
        module_id=module.id,
        call_type="direction_change_outline",
        **resolve_model_config(),
    )
    return validate_llm_json(raw, CourseDirectionChangeSchema)


def _activity_type_usage_summary(course: Course, up_to_module_position: int) -> str:
    """Summarize which activity types already appear in a course's already-committed modules.

    module_direction_outline.md only ever sees the modules being replanned,
    via assemble_learning_history()'s prose digests - it has no visibility
    into what activity types earlier, uncommitted-to-replan modules already
    used, so a replanned tail could otherwise violate the once/twice-per-
    course activity rules (docs/course_content_definitions.md) without this.
    Counts real generated Activity rows, not planned-but-ungenerated ones,
    since only generated modules are truly "used." Same inclusive
    up_to_module_position convention as assemble_learning_history() ("at or
    before this position").

    Args:
        course: The course being replanned.
        up_to_module_position: Only modules at or before this position count
            as already committed.

    Returns:
        A short summary line per activity type actually present, or a
        one-line fallback when nothing's been generated yet.
    """
    counts: dict[str, int] = {}
    for module in course.modules:
        if module.position > up_to_module_position:
            continue
        for activity in module.activities:
            counts[activity.activity_type] = counts.get(activity.activity_type, 0) + 1

    if not counts:
        return "No activities have been generated yet in this course."
    return "Activity types already used earlier in this course: " + ", ".join(
        f"{count} {activity_type}" for activity_type, count in sorted(counts.items())
    )


def _mock_direction_change(module: Module, revision_feedback: str | None) -> CourseDirectionChangeSchema:
    suffix = " (revised)" if revision_feedback else ""
    return CourseDirectionChangeSchema(
        modules=[
            CourseModuleSchema(
                title=f"[MOCK] New Direction{suffix}",
                description="[MOCK] A module reflecting the new direction.",
                estimatedTimeline="1 week",
                learningOutcomes=["[MOCK] Understand the new direction"],
                plannedActivities=[
                    PlannedActivitySchema(
                        type="reading", title="[MOCK] Introduction", plan="[MOCK] Cover the fundamentals."
                    ),
                    PlannedActivitySchema(
                        type="assessment", title="[MOCK] Check Your Understanding", plan="[MOCK] Quiz the basics."
                    ),
                ],
            ),
        ],
    )


def _get_course_or_raise(course_id: str) -> Course:
    course = db.session.get(Course, course_id)
    if course is None:
        raise CourseNotFoundError(f"No course with id '{course_id}'")
    return course


def _add_message(course_id: str, role: str, kind: str, content: str, module_id: str | None = None) -> None:
    db.session.add(
        ConversationMessage(course_id=course_id, role=role, kind=kind, content=content, module_id=module_id)
    )


def _get_module_or_raise(module_id: str) -> Module:
    module = db.session.get(Module, module_id)
    if module is None:
        raise ModuleNotFoundError(f"No module with id '{module_id}'")
    return module


def _ingest_source_materials(
    course: Course, files: list[FileStorage] | None, supplement_with_web_search: bool = False
) -> None:
    """Extract, chunk, embed, summarize, and persist any documents attached to this interview turn.

    Writes each file's extracted text to disk, chunks it and adds the
    chunks to the course's vector index (see vector_store.py), and adds a
    SourceMaterial row to the session — but doesn't itself commit: if
    extraction raises partway through (e.g. an unsupported or corrupt
    file), nothing from this call — not the course, not the interview-answer
    message, not any file already processed in this same call — ends up
    persisted, since the caller's single db.session.commit() never runs.
    resolve_model_config()/resolve_embedding_config() can trigger their own
    nested commit on first use (UserSettings.get_or_create()), which is why
    callers must call this before adding the course/message to the session
    themselves, not after.

    Args:
        course: The course these materials belong to.
        files: The uploaded files, or None/empty if none were attached.
        supplement_with_web_search: If true, module generation will also
            search the web to supplement these documents rather than
            grounding solely in them (see module_generation.py). OR'd onto
            course.web_search_supplement_enabled, not overwritten - a
            learner can opt in on any upload across multiple interview
            turns, and it stays on for the course from then on. No effect
            if files is empty (nothing to opt in *for* in that case).

    Raises:
        DocumentExtractionError: If a file's text can't be extracted.
        EmbeddingNotConfiguredError: If no embedding model is set (needed
            to chunk/embed the attached document).
    """
    files = [f for f in (files or []) if f and f.filename]
    if not files:
        return

    course.web_search_supplement_enabled = course.web_search_supplement_enabled or supplement_with_web_search

    model_config = resolve_model_config()
    embedding_config = resolve_embedding_config()
    for file_storage in files:
        content = file_storage.read()
        text = extract_text(file_storage.filename, content)
        source_material = SourceMaterial(id=str(uuid4()), file_name=file_storage.filename, text_path="")
        source_material.text_path = save_source_material_text(source_material.id, text)

        chunks = chunk_pages(file_storage.filename, extract_pages(file_storage.filename, content))
        # Sets course.vector_index_path itself (see below) so a second file
        # in this same call - or a document attached on a later interview
        # turn - appends to the same course-level index instead of
        # overwriting it.
        course.vector_index_path = build_or_update_index(course, chunks, embedding_config)
        source_material.interview_summary = summarize_document_for_interview(
            chunks, model_config, embedding_config, course_id=course.id
        )

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
        return InterviewStepSchema(coverage="max questions reached", done=True, question="(interview complete)")

    if current_app.config.get("LLM_TEST_MODE"):
        if course.source_materials:
            filenames = ", ".join(m.file_name for m in course.source_materials)
            return InterviewStepSchema(
                coverage="[MOCK] coverage note",
                done=False,
                question=f"[MOCK] Follow-up question {questions_asked + 1} about {filenames}.",
            )
        return InterviewStepSchema(
            coverage="[MOCK] coverage note",
            done=False,
            question=f"[MOCK] Follow-up question {questions_asked + 1} about your goals.",
        )

    system_prompt = load_prompt(
        "course_interview",
        questions_asked=questions_asked,
        max_questions=MAX_INTERVIEW_QUESTIONS,
        source_materials=render_source_material_summaries(course),
        parent_context=_parent_context(course),
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course, {"interview_answer", "interview_question"}
    )
    raw = complete(
        messages=messages,
        schema=InterviewStepSchema,
        course_id=course.id,
        call_type="interview_question",
        **resolve_model_config(),
    )
    return validate_llm_json(raw, InterviewStepSchema)


def _parent_context(course: Course) -> str:
    """Format what the learner already covered in a "Branch Off" course's parent, if any.

    Empty string for an ordinary (non-branched) course, or if the parent
    somehow no longer exists — matches every other optional prompt section's
    empty-string-means-omit convention (see render_source_material_summaries()).

    No up_to_module_position truncation needed: a module only gets a
    module_learning_digest once its content is actually generated (see
    module_generation.py), which only happens once the learner reaches it —
    so a parent's assembled history already naturally stops exactly at
    "Branch Off"'s trigger point (the module that was just completed, whose
    digest was generated back when the learner first reached it) without
    needing to track or pass a position explicitly.

    Args:
        course: The (possibly branched) course being generated for.

    Returns:
        The parent's assembled learning history, or "" if not a branch.
    """
    if not course.parent_course_id:
        return ""
    parent = db.session.get(Course, course.parent_course_id)
    if parent is None:
        return ""
    return assemble_learning_history(parent)


def _generate_outline_content(course: Course, revision_feedback: str | None) -> CourseOutlineSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_outline(course, revision_feedback)

    system_prompt = load_prompt(
        "course_outline",
        source_materials=render_source_material_summaries(course),
        parent_context=_parent_context(course),
        activity_type_reference=load_prompt("activity_type_reference"),
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course, {"interview_answer", "interview_question", "outline_revision_request", "outline_presented"}
    )
    raw = complete(
        messages=messages,
        schema=CourseOutlineSchema,
        course_id=course.id,
        call_type="course_outline",
        **resolve_model_config(),
    )
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
