"""Ask Me Anything: a chat scoped strictly to the learner's own course materials.

Three plain, deterministic complete() calls, the same pattern every other
generation flow in this app already uses, not model-driven tool-calling
(see retrieval_agent.py, kept but deliberately not revived here):
1. Classify which of the learner's courses (up to 3) could plausibly answer
   the question, from a candidate list of courses that actually have a
   vector index.
2. Retrieve the top chunks from each selected course's index and merge them.
3. Answer strictly from those chunks, declining if they don't cover it.

No persistence anywhere - the frontend resends its own transcript each
turn, same as the "ephemeral" decision recorded in the Resources plan.
"""

from dataclasses import dataclass, field

from flask import current_app

from app.extensions import db
from app.models import Course
from app.services.document_chunking import Chunk
from app.services.llm import complete
from app.services.llm_schemas import AMAAnswerSchema, CitationSchema, CourseSelectionSchema, validate_llm_json
from app.services.model_selection import EmbeddingNotConfiguredError, resolve_embedding_config, resolve_model_config
from app.services.prompts import load_prompt
from app.services.vector_store import query as query_vector_store

# Matches CourseSelectionSchema.courseIds's max_length - retrieval is capped
# to this many courses' indexes regardless of how many the classifier picks.
MAX_COURSES = 3
# Down from module_generation.py's MAX_CHUNKS_PER_ACTIVITY (6) for a single
# course, since here the merged pool can draw from up to MAX_COURSES indexes
# at once - keeps the merged context a reasonable size even at 3 courses.
CHUNKS_PER_COURSE = 4

DECLINE_NO_COURSES = (
    "None of your courses have searchable material yet, so I can't answer from your course "
    "content. Once a course finishes generating (with an embedding model configured), ask again."
)
DECLINE_OFF_TOPIC = (
    "That doesn't look like it's covered in your course materials, so I can't answer it here. "
    "Try asking something closer to what your courses actually cover."
)


@dataclass
class AMAResult:
    """One AMA turn's result: Bonsai's reply, which courses it drew from, and citations."""

    reply: str
    course_ids: list[str] = field(default_factory=list)
    citations: list[CitationSchema] = field(default_factory=list)


def answer_ama_question(message: str, history: list[dict]) -> AMAResult:
    """Answer a learner's question strictly from their own course materials.

    Args:
        message: The learner's latest message.
        history: Prior turns in this chat, each ``{"role", "content"}``,
            oldest first. Not persisted - the frontend owns this transcript.

    Returns:
        Bonsai's reply, the course ids it drew from (if any), and citations.

    Raises:
        LLMOutputValidationError: If a model response doesn't match its schema.
    """
    candidates = list(db.session.execute(db.select(Course).where(Course.vector_index_path.isnot(None))).scalars())
    if not candidates:
        return AMAResult(reply=DECLINE_NO_COURSES)

    try:
        embedding_config = resolve_embedding_config()
    except EmbeddingNotConfiguredError:
        return AMAResult(reply=DECLINE_NO_COURSES)

    selected_ids = _select_courses(message, history, candidates)
    # Never trust a raw model-authored id against the real candidate set -
    # silently drop anything hallucinated, same precedent as reading
    # citations/correctAnswerIndex elsewhere in this codebase.
    candidates_by_id = {c.id: c for c in candidates}
    selected = [candidates_by_id[cid] for cid in selected_ids if cid in candidates_by_id][:MAX_COURSES]
    if not selected:
        return AMAResult(reply=DECLINE_OFF_TOPIC)

    chunks_by_course = _retrieve_chunks(selected, message, embedding_config)
    merged = [(course, chunk) for course, chunks in chunks_by_course for chunk in chunks]
    if not merged:
        return AMAResult(reply=DECLINE_OFF_TOPIC)

    reply = _answer_from_chunks(message, history, merged)
    citations = [CitationSchema(label=f"{course.title}: {_chunk_citation_label(chunk)}", url=chunk.url) for course, chunk in merged]
    return AMAResult(reply=reply, course_ids=[c.id for c in selected], citations=citations)


def _select_courses(message: str, history: list[dict], candidates: list[Course]) -> list[str]:
    if current_app.config.get("LLM_TEST_MODE"):
        return [candidates[0].id]

    system_prompt = load_prompt(
        "ama_course_selection",
        courses="\n".join(f"- {c.id}: {c.title} — {c.description}" for c in candidates),
    )
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    raw = complete(
        messages=messages,
        schema=CourseSelectionSchema,
        call_type="ama_course_selection",
        label=message,
        **resolve_model_config(),
    )
    return validate_llm_json(raw, CourseSelectionSchema).courseIds


def _retrieve_chunks(courses: list[Course], message: str, embedding_config: dict) -> list[tuple[Course, list[Chunk]]]:
    results = []
    for course in courses:
        chunk_results = query_vector_store(course, [message], embedding_config, top_k=CHUNKS_PER_COURSE)
        results.append((course, chunk_results.get(0, [])))
    return results


def _answer_from_chunks(message: str, history: list[dict], merged: list[tuple[Course, Chunk]]) -> str:
    if current_app.config.get("LLM_TEST_MODE"):
        return "[MOCK] Based on your course materials, here's the answer."

    excerpts = "\n\n".join(f"[{course.title}] {_chunk_citation_label(chunk)}:\n{chunk.text}" for course, chunk in merged)
    system_prompt = load_prompt("ama_answer", excerpts=excerpts)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    raw = complete(
        messages=messages,
        schema=AMAAnswerSchema,
        call_type="ama_answer",
        label=message,
        **resolve_model_config(),
    )
    return validate_llm_json(raw, AMAAnswerSchema).answer


def _chunk_citation_label(chunk: Chunk) -> str:
    return f"{chunk.source}, p. {chunk.page}" if chunk.page is not None else chunk.source
