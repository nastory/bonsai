"""Ask Me Anything: a chat scoped strictly to the learner's own course materials.

Four plain, deterministic complete() calls, the same pattern every other
generation flow in this app already uses, not model-driven tool-calling
(see retrieval_agent.py, kept but deliberately not revived here):
1. Rewrite the learner's message into search-optimized terms - a raw
   conversational question (especially a follow-up) often embeds poorly
   against a vector index, so this happens before anything else and both
   later steps work from its output rather than the learner's literal
   wording.
2. Classify which of the learner's courses (up to 3) could plausibly answer
   the question, from a candidate list of courses that actually have a
   vector index.
3. Retrieve the top chunks from each selected course's index (queried with
   the optimized terms, not the raw message) and merge them.
4. Answer strictly from those chunks, declining if they don't cover it -
   this step alone uses the learner's actual wording, since it's what gets
   read back to them.

No persistence anywhere - the frontend resends its own transcript each
turn, same as the "ephemeral" decision recorded in the Resources plan.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import zip_longest

from flask import current_app

from app.extensions import db
from app.models import Course
from app.services.document_chunking import Chunk
from app.services.llm import complete
from app.services.llm_schemas import (
    AMAAnswerSchema,
    AMASearchTermsSchema,
    CitationSchema,
    CourseSelectionSchema,
    validate_llm_json,
)
from app.services.model_selection import EmbeddingNotConfiguredError, resolve_embedding_config, resolve_model_config
from app.services.prompts import load_prompt
from app.services.vector_store import query as query_vector_store

# Matches CourseSelectionSchema.courseIds's max_length - retrieval is capped
# to this many courses' indexes regardless of how many the classifier picks.
MAX_COURSES = 3
# Matches module_generation.py's MAX_CHUNKS_PER_ACTIVITY. Raised from an
# earlier 4 - too tight in practice (confirmed live: a real course with
# real content still came back with too little grounding for a
# conversational question, which asks a broader question than one lesson
# activity's narrow, already-known topic does). No similarity threshold
# exists anywhere in vector_store.py to tune alongside this - query()
# always returns its top_k nearest neighbors by raw FAISS distance, however
# weak the match, so retrieval breadth is controlled entirely by this
# constant (and by how many search terms feed it - see _retrieve_chunks()).
CHUNKS_PER_COURSE = 6

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

    search_terms = _optimize_search_terms(message, history)

    selected_ids = _select_courses(search_terms, history, candidates)
    # Never trust a raw model-authored id against the real candidate set -
    # silently drop anything hallucinated, same precedent as reading
    # citations/correctAnswerIndex elsewhere in this codebase.
    candidates_by_id = {c.id: c for c in candidates}
    selected = [candidates_by_id[cid] for cid in selected_ids if cid in candidates_by_id][:MAX_COURSES]
    if not selected:
        return AMAResult(reply=DECLINE_OFF_TOPIC)

    chunks_by_course = _retrieve_chunks(selected, search_terms, embedding_config)
    merged = [(course, chunk) for course, chunks in chunks_by_course for chunk in chunks]
    if not merged:
        return AMAResult(reply=DECLINE_OFF_TOPIC)

    reply = _answer_from_chunks(message, history, merged)
    citations = [CitationSchema(label=f"{course.title}: {_chunk_citation_label(chunk)}", url=chunk.url) for course, chunk in merged]
    return AMAResult(reply=reply, course_ids=[c.id for c in selected], citations=citations)


def _optimize_search_terms(message: str, history: list[dict]) -> list[str]:
    if current_app.config.get("LLM_TEST_MODE"):
        return [message]

    system_prompt = load_prompt("ama_search_terms")
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    raw = complete(
        messages=messages,
        schema=AMASearchTermsSchema,
        call_type="ama_search_terms",
        label=message,
        **resolve_model_config(),
    )
    return validate_llm_json(raw, AMASearchTermsSchema).terms


def _select_courses(search_terms: list[str], history: list[dict], candidates: list[Course]) -> list[str]:
    if current_app.config.get("LLM_TEST_MODE"):
        return [candidates[0].id]

    system_prompt = load_prompt(
        "ama_course_selection",
        courses="\n".join(f"- {c.id}: {c.title} — {c.description}" for c in candidates),
    )
    query = "\n".join(search_terms)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": query}]
    raw = complete(
        messages=messages,
        schema=CourseSelectionSchema,
        call_type="ama_course_selection",
        label=query,
        **resolve_model_config(),
    )
    return validate_llm_json(raw, CourseSelectionSchema).courseIds


def _retrieve_chunks(
    courses: list[Course], search_terms: list[str], embedding_config: dict
) -> list[tuple[Course, list[Chunk]]]:
    """Query each selected course's vector index concurrently, with every search term.

    Each course has its own on-disk FAISS index (see vector_store.py), so
    these reads are fully independent - no shared mutable state between
    them, unlike course_generation.py's document-ingestion loop (which
    writes into one shared per-course index and must stay sequential).
    Threaded rather than batched into one call since each course's
    embed() call hits a different, per-course index; this is the same
    "independent I/O, thread it" precedent module_retrieval.py's
    retrieve_for_module() already established for concurrent Tavily
    searches within a module.

    Every search term is queried against a course's index (one batched
    embed() call handles all of them at once - see vector_store.query()),
    then merged/deduped down to CHUNKS_PER_COURSE per course: different
    phrasings can surface different relevant chunks, so this widens what's
    considered before narrowing back down to a bounded amount of context.
    """
    # current_app is a context-local proxy, not shared automatically across
    # threads: each worker needs its own pushed app context (via the
    # captured real app object) before query_vector_store()/embed() can
    # read current_app.config, same as module_retrieval.py's worker.
    app = current_app._get_current_object()

    def _worker(course: Course) -> tuple[Course, list[Chunk]]:
        with app.app_context():
            chunk_results = query_vector_store(course, search_terms, embedding_config, top_k=CHUNKS_PER_COURSE)
            per_term = [chunk_results.get(i, []) for i in range(len(search_terms))]
            return course, _merge_term_results(per_term)[:CHUNKS_PER_COURSE]

    with ThreadPoolExecutor(max_workers=len(courses)) as executor:
        return list(executor.map(_worker, courses))


def _merge_term_results(term_chunk_lists: list[list[Chunk]]) -> list[Chunk]:
    """Round-robin merge each search term's ranked chunk list into one, deduped.

    vector_store.query() only ranks chunks within one query - there's no
    cross-query relevance score to globally re-sort by - so this
    interleaves each term's own top pick first rather than exhausting one
    term's results before ever considering the next, a fairer blend across
    phrasings than raw concatenation.
    """
    seen: set[tuple[str, int | None, str]] = set()
    merged: list[Chunk] = []
    for chunks_at_rank in zip_longest(*term_chunk_lists):
        for chunk in chunks_at_rank:
            if chunk is None:
                continue
            key = (chunk.source, chunk.page, chunk.text)
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)
    return merged


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
