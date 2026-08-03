"""Condenses a course's interview + outline into a persistent, structured memory.

Generated once, at outline approval (see course_generation.py's
approve_outline()), so it exists before any module generation can ever run.
Downstream consumers (module generation now, branching later) read
Course.context_summary via render_course_context()/assemble_learning_history()
instead of replaying the full interview conversation on every call.
"""

from flask import current_app

from app.models import Course
from app.services.llm import complete
from app.services.llm_schemas import CourseContextSchema, DocumentSummarySchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt
from app.services.source_material_storage import load_source_material_text


def compact_course_context(course: Course) -> CourseContextSchema:
    """Condense a course's interview conversation and approved outline into a persistent memory.

    Args:
        course: The course, with its conversation and modules already populated.

    Returns:
        The condensed course context.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_course_context(course)

    system_prompt = load_prompt("course_context_compaction")
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course,
        {"interview_answer", "interview_question", "outline_revision_request", "outline_presented", "outline_approved"},
    )
    raw = complete(messages=messages, schema=CourseContextSchema, **resolve_model_config())
    return validate_llm_json(raw, CourseContextSchema)


def render_course_context(course: Course) -> str:
    """Format a course's compacted context into prompt-ready text.

    Args:
        course: The course whose context_summary should be rendered.

    Returns:
        A short block of text summarizing the course, or an empty string if
        the course has no context_summary yet (e.g. a course created before
        this existed, or one that never went through the interview flow).
    """
    ctx = course.context_summary
    if not ctx:
        return ""

    lines = [f"Course summary: {ctx.get('summary', '')}", f"Learner profile: {ctx.get('learnerProfile', '')}"]
    key_decisions = ctx.get("keyDecisions") or []
    if key_decisions:
        lines.append("Key decisions: " + "; ".join(key_decisions))
    return "\n".join(lines)


def summarize_document_for_interview(text: str, model_config: dict) -> str:
    """Condense an attached document's extracted text to a short interview-shaping summary.

    Called once per document at ingestion time (see course_generation.py's
    _ingest_source_materials()) and persisted onto SourceMaterial.interview_summary,
    so the interview never re-sends (or re-summarizes) the full document text
    on every turn. Outline/module generation still use the full text via
    render_source_materials() — this summary is interview-specific.

    Args:
        text: The document's extracted text.
        model_config: Resolved model/provider settings (see model_selection.py).

    Returns:
        A summary of at most 3 sentences.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return "[MOCK] Summary of the document."

    prompt = load_prompt("document_summary")
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": text}]
    raw = complete(messages=messages, schema=DocumentSummarySchema, **model_config)
    return validate_llm_json(raw, DocumentSummarySchema).summary


def render_source_material_summaries(course: Course) -> str:
    """Format a course's uploaded source materials' interview summaries for the interview prompt.

    Args:
        course: The course whose source materials should be rendered.

    Returns:
        Each material's interview_summary under a "--- filename ---" header,
        concatenated, or an empty string if the course has none. Materials
        without a summary yet (shouldn't happen in practice — ingestion
        always computes one) are skipped.
    """
    if not course.source_materials:
        return ""

    parts = [
        f"--- {material.file_name} ---\n{material.interview_summary}"
        for material in course.source_materials
        if material.interview_summary
    ]
    return "\n\n".join(parts)


def render_source_materials(course: Course) -> str:
    """Format a course's uploaded source materials' extracted text for a prompt.

    Used for outline and module generation, which each render this once per
    call rather than on every turn — the interview uses the much shorter
    render_source_material_summaries() instead, since it's re-sent every turn.

    Args:
        course: The course whose source materials should be rendered.

    Returns:
        Each material's extracted text under a "--- filename ---" header,
        concatenated, or an empty string if the course has none.
    """
    if not course.source_materials:
        return ""

    parts = [
        f"--- {material.file_name} ---\n{load_source_material_text(material.text_path)}"
        for material in course.source_materials
    ]
    return "\n\n".join(parts)


def assemble_learning_history(course: Course, up_to_module_position: int | None = None) -> str:
    """Assemble everything module generation should know about a course so far.

    Concatenates the course's compacted context with the condensed learning
    digest from each prior module, in module order, so generation for module
    N has real continuity with modules 1..N-1 without replaying their full
    content.

    Args:
        course: The course to assemble history for.
        up_to_module_position: If given, only include digests for modules at
            or before this position. Nothing in the current generation flow
            passes this — it's the truncation hook a future branch/extend
            flow (Phase 2) will use to continue from, or exclude history
            after, a specific point in a course's history.

    Returns:
        The assembled history as prompt-ready text.
    """
    position_by_module_id = {m.id: m.position for m in course.modules}
    digests = [
        m for m in course.conversation if m.kind == "module_learning_digest" and m.module_id is not None
    ]
    if up_to_module_position is not None:
        digests = [d for d in digests if position_by_module_id.get(d.module_id, -1) <= up_to_module_position]
    digests.sort(key=lambda d: position_by_module_id.get(d.module_id, 0))

    parts = [render_course_context(course), *(d.content for d in digests)]
    return "\n\n".join(p for p in parts if p)


def conversation_turns(course: Course, kinds: set[str]) -> list[dict[str, str]]:
    """Build a real chat-message list from a course's conversation, for the given message kinds.

    ConversationMessage.role is already exactly "user"/"assistant" (see
    course_generation.py's _add_message()), so this is a direct mapping —
    no reinterpretation needed. Replaces flattening the conversation into a
    single "Learner: ...\\nBonsai: ..." text block: the chat-completions API
    already has a native way to represent a real conversation.

    Args:
        course: The course whose conversation should be turned into messages.
        kinds: Which ConversationMessage.kind values to include, so a given
            call only sees the parts of the conversation relevant to it.

    Returns:
        Messages in standard role/content shape, in conversation order.
    """
    return [{"role": m.role, "content": m.content} for m in course.conversation if m.kind in kinds and m.content]


def _mock_course_context(course: Course) -> CourseContextSchema:
    return CourseContextSchema(
        summary=f"[MOCK] A condensed summary of {course.title}.",
        learnerProfile="[MOCK] Condensed learner background and goals.",
        keyDecisions=[],
    )
