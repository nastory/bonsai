"""Generates a module's learning activities.

Per docs/course_creation_websearch_flow.md: a module's activities were
already planned at outline time (see course_generation.py's Module.activity_plan),
so generation's job is to search for material and write content for each
one, not invent them from scratch. Grounding happens deliberately, up
front for the whole module, rather than being left to a model-driven
tool-calling loop, and always ends up in the same place regardless of
source: the course's vector index (see vector_store.py). Web-search-grounded
courses still plan search terms and fetch via Tavily up front (see
module_retrieval.py - an LLM is genuinely needed there to phrase good
queries against an arbitrary web corpus), but the fetched content is then
chunked and embedded into the course's index rather than used raw, exactly
like an uploaded document is. Every activity then retrieves its own most
relevant chunks from that shared index - the activity's own title+plan,
embedded directly, is the query, since there's no need for an LLM to
creatively phrase a query against material that's already in hand (either
just-fetched or previously uploaded). Activities are then generated one at
a time as a running chat history, so each one's content has real continuity
with the one before it. Once the module's activities are generated, a
condensed digest is persisted to the course's learning history (see
course_context.py), so later modules build on this one.

Reuses the same schema-validation, mocking, and model-resolution patterns
established for course generation (see course_generation.py): canned
activities in LLM_TEST_MODE, the real complete() -> resolve_model_config()
path otherwise, and each activity's content-heavy fields are written to
disk via content_storage, per the hybrid storage model.

Disclosed tradeoff: since each prior activity's full generated content
stays in the chat history for the rest of that module's generation,
cumulative prompt size grows with every activity. Confirmed against a real
local Ollama/llama3 that this can exhaust a small default context window
partway through a module, producing a truncated/malformed response rather
than a clean failure. Accepted for now as a local/BYOM-model limitation,
consistent with other disclosed tradeoffs in this codebase for weaker
models (e.g. retrieval_agent.py's old tool-use caveat) rather than fixed
by capping history size or configuring a larger context window. Document
grounding at least no longer makes this worse with document size (see
vector_store.py) - only the number of retrieved chunks per activity, a
small fixed cap, affects prompt size now, not the source document's length.
"""

from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import Activity, ConversationMessage, Module, UserSettings
from app.services.content_storage import save_activity_content
from app.services.course_context import assemble_learning_history, render_source_materials
from app.services.document_chunking import Chunk, chunk_pages
from app.services.llm import complete
from app.services.llm_schemas import (
    CitationSchema,
    GeneratedActivitySchema,
    GeneratedQuizActivityDecodingSchema,
    ModuleDigestSchema,
    validate_llm_json,
)
from app.services.model_selection import resolve_embedding_config, resolve_model_config
from app.services.module_retrieval import plan_activity_searches, retrieve_for_module
from app.services.prompts import load_prompt
from app.services.vector_store import build_or_update_index
from app.services.vector_store import query as query_vector_store

# Per-activity cap on retrieved document chunks - mirrors module_retrieval.py's
# MAX_RESULTS_PER_ACTIVITY (3) for the web-search path: enough for a
# well-grounded activity without flooding the generation prompt.
MAX_CHUNKS_PER_ACTIVITY = 4


class ModuleNotFoundError(Exception):
    """Raised when a module-generation operation targets an unknown module id."""


def generate_module_activities(module_id: str) -> Module:
    """Generate and persist a module's learning activities, unless it already has some.

    Idempotent: a module that already has activities (the learner revisits
    it, or the trigger fires twice) is returned unchanged rather than
    generating duplicate content.

    Args:
        module_id: The module's id.

    Returns:
        The module, with its activities populated.

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    if module.activities:
        return module

    generated = _generate_activities_content(module)
    # All available, never locked: a module's activities are generated
    # together in this one call, so there's no such thing as "generated but
    # not reachable yet" for an activity the way there is for a module that
    # hasn't been generated at all.
    activities = [
        Activity(
            id=str(uuid4()),
            position=i,
            activity_type=a.type,
            title=a.title,
            status="available",
            estimated_minutes=a.estimatedMinutes,
        )
        for i, a in enumerate(generated)
    ]

    for activity, a in zip(activities, generated):
        content = a.model_dump(exclude={"type", "title", "estimatedMinutes"})
        activity.content_path = save_activity_content(activity.id, content)

    module.activities = activities
    _generate_and_persist_digest(module)
    db.session.commit()
    return module


def _get_module_or_raise(module_id: str) -> Module:
    module = db.session.get(Module, module_id)
    if module is None:
        raise ModuleNotFoundError(f"No module with id '{module_id}'")
    return module


def _generate_activities_content(module: Module) -> list[GeneratedActivitySchema]:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_activities(module)

    model_config = resolve_model_config()
    results_by_activity: dict[int, list[dict]] = {}
    citations_by_activity: dict[int, list[CitationSchema]] = {}

    if not module.course.source_materials:
        # Web-grounded: an LLM is still needed to plan good search terms
        # (unlike document/already-fetched-web material, there's no way to
        # query an arbitrary web corpus by embedding alone) - planned
        # unconditionally, same as before this change, even without a
        # Tavily key configured (retrieve_for_module() already returns empty
        # results for every activity in that case, same as today). The
        # fetched content is then chunked and embedded into the course's
        # vector index rather than used raw - same storage/retrieval
        # mechanism a document gets, just fed by a fresh Tavily fetch
        # instead of an upload. Guarded by `if web_chunks` so a key-less or
        # empty-results course never pays for an embedding call it doesn't
        # need.
        settings = UserSettings.get_or_create()
        search_plan = plan_activity_searches(module, model_config)
        search_results = retrieve_for_module(
            module, search_plan, settings.tavily_api_key, settings.deep_search_enabled
        )
        web_chunks = [
            chunk
            for results in search_results.values()
            for r in results
            for chunk in chunk_pages(r["title"], [(None, r["content"])], url=r["url"])
        ]
        if web_chunks:
            embedding_config = resolve_embedding_config()
            module.course.vector_index_path = build_or_update_index(module.course, web_chunks, embedding_config)

    if module.course.vector_index_path:
        # Covers document-grounded, web-grounded (just indexed above if this
        # course had no index yet), and - once a future opt-in supplement
        # feature ships - both at once. One retrieval mechanism regardless
        # of source: the activity's own title+plan, embedded directly, is
        # the query, since there's no need for an LLM to creatively phrase a
        # query against material that's already in hand (either just-fetched
        # or previously uploaded). One batched embedding call for every
        # activity in the module, then fast local FAISS searches - no
        # threading needed, there's no per-activity network I/O here the way
        # Tavily fetches themselves have.
        embedding_config = resolve_embedding_config()
        queries = [f"{a['title']}: {a['plan']}" for a in module.activity_plan]
        chunk_results = query_vector_store(module.course, queries, embedding_config, top_k=MAX_CHUNKS_PER_ACTIVITY)
        results_by_activity = {
            i: [{"source": _chunk_citation_label(c), "content": c.text} for c in chunks]
            for i, chunks in chunk_results.items()
        }
        citations_by_activity = {
            i: [CitationSchema(label=_chunk_citation_label(c), url=c.url) for c in chunks]
            for i, chunks in chunk_results.items()
        }
    # else: source materials exist but no index yet (ingested before
    # chunking/embedding was added, or embedding failed at ingestion time) -
    # no per-activity retrieval is possible. Falls through to
    # _module_seed_data_message()'s own legacy whole-document fallback below
    # instead of leaving these activities completely ungrounded.

    messages = [
        {"role": "system", "content": load_prompt("module_activity_generation")},
        {"role": "user", "content": _module_seed_data_message(module)},
    ]
    generated: list[GeneratedActivitySchema] = []
    for i, planned in enumerate(module.activity_plan):
        turn = _activity_turn_message(i, module.activity_plan, planned, results_by_activity.get(i, []))
        messages.append({"role": "user", "content": turn})
        # Quiz/assessment calls get a stricter decoding-only schema (with
        # correctAnswerIndex/explanation genuinely required, not Optional as
        # they are on GeneratedActivitySchema, which every other activity
        # type also shares) — see GeneratedQuizActivityDecodingSchema's
        # docstring for why this actually matters, not just belt-and-suspenders.
        decoding_schema = (
            GeneratedQuizActivityDecodingSchema
            if planned["type"] in ("quiz", "assessment")
            else GeneratedActivitySchema
        )
        raw = complete(messages=messages, schema=decoding_schema, **model_config)
        parsed = validate_llm_json(raw, GeneratedActivitySchema)
        if planned["type"] == "reading" and i in citations_by_activity:
            # Deterministic, not model-authored, for both document and web
            # sources now: we already know exactly which chunks were
            # retrieved and handed to this activity, so there's no reason to
            # trust the model to correctly echo back a source/page/url -
            # same reasoning as correctAnswerIndex replacing text-matching
            # for quizzes.
            parsed = parsed.model_copy(update={"citations": citations_by_activity[i]})
        generated.append(parsed)
        messages.append({"role": "assistant", "content": raw})

    return generated


def _chunk_citation_label(chunk: Chunk) -> str:
    return f"{chunk.source}, p. {chunk.page}" if chunk.page is not None else chunk.source


def _module_seed_data_message(module: Module) -> str:
    outcomes = "\n".join(f"- {outcome}" for outcome in module.learning_outcomes)
    parts = [
        assemble_learning_history(module.course),
        f"Module: {module.title}\n{module.description}",
        f"This module's learning outcomes:\n{outcomes}",
        f"The full planned sequence of activities for this module:\n{_format_activity_plan(module.activity_plan)}",
    ]
    if module.course.source_materials and not module.course.vector_index_path:
        # Legacy fallback: see _generate_activities_content()'s matching
        # comment - only reached when chunking/embedding wasn't available
        # at ingestion time. Whole-document-in-one-block is worse for large
        # documents (see this module's docstring) but strictly better than
        # no grounding at all for these older courses.
        source_materials = render_source_materials(module.course)
        if source_materials:
            parts.append(
                "Source materials the learner has provided for this course (this course is grounded entirely in "
                "this document — no web search is used, so treat this as the primary source for every activity's "
                "content):\n" + source_materials
            )
    return "\n\n".join(p for p in parts if p)


def _activity_turn_message(index: int, activity_plan: list[dict], planned: dict, results: list[dict]) -> str:
    lines = [f"Now write activity {index + 1} of {len(activity_plan)}: [{planned['type']}] {planned['title']}"]
    lines.append(planned["plan"])
    if results:
        lines.append(
            "Excerpts to ground this activity in (do not write your own citations for this — Bonsai "
            "attaches the correct source automatically):"
        )
        lines.extend(f"- {r['source']}: {r['content']}" for r in results)
    else:
        lines.append(
            "No material is available for this activity; ground it in any source materials provided "
            "above, or rely on your own knowledge if none were provided."
        )
    return "\n".join(lines)


def _format_activity_plan(activity_plan: list[dict]) -> str:
    return "\n".join(f"{i}. [{a['type']}] {a['title']}: {a['plan']}" for i, a in enumerate(activity_plan))


def _generate_and_persist_digest(module: Module) -> None:
    digest = _generate_digest_content(module)
    db.session.add(
        ConversationMessage(
            course_id=module.course_id,
            module_id=module.id,
            role="assistant",
            kind="module_learning_digest",
            content=digest.digest,
        )
    )


def _generate_digest_content(module: Module) -> ModuleDigestSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return ModuleDigestSchema(digest=f"[MOCK] Digest of {module.title}.")

    messages = [
        {"role": "system", "content": load_prompt("module_digest")},
        {"role": "user", "content": _digest_data_message(module)},
    ]
    raw = complete(messages=messages, schema=ModuleDigestSchema, **resolve_model_config())
    return validate_llm_json(raw, ModuleDigestSchema)


def _digest_data_message(module: Module) -> str:
    return f"Module: {module.title}\n{module.description}\n\nGenerated activities:\n{_format_generated_activities(module)}"


def _format_generated_activities(module: Module) -> str:
    lines = []
    for activity in module.activities:
        content = activity.to_dict()
        text = content.get("body") or content.get("prompt") or content.get("question") or ""
        lines.append(f"- [{activity.activity_type}] {activity.title}: {text[:300]}")
    return "\n".join(lines)


def _mock_activities(module: Module) -> list[GeneratedActivitySchema]:
    return [_mock_activity(planned) for planned in module.activity_plan]


def _mock_activity(planned: dict) -> GeneratedActivitySchema:
    activity_type = planned["type"]
    title = f"[MOCK] {planned['title']}"

    if activity_type == "reading":
        return GeneratedActivitySchema(
            type=activity_type,
            title=title,
            estimatedMinutes=15,
            body=f"[MOCK] A guided reading covering {planned['title']}.",
            citations=[CitationSchema(label="[MOCK] Example Source", url="https://example.com/mock-source")],
        )
    if activity_type in ("essay", "project", "discussion"):
        return GeneratedActivitySchema(
            type=activity_type,
            title=title,
            estimatedMinutes=15,
            prompt=f"[MOCK] {planned['plan']}",
        )
    return GeneratedActivitySchema(
        type=activity_type,
        title=title,
        estimatedMinutes=10,
        question=f"[MOCK] Check: {planned['plan']}",
        options=["[MOCK] Option A", "[MOCK] Option B"],
        correctAnswerIndex=0,
        explanation="[MOCK] Explanation of why this is correct.",
    )
