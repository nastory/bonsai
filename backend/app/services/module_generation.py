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

from dataclasses import dataclass
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
    ModuleSearchPlanSchema,
    VideoSelectionSchema,
    VisualAidPlanSchema,
    validate_llm_json,
)
from app.services.model_selection import EmbeddingNotConfiguredError, resolve_embedding_config, resolve_model_config
from app.services.module_retrieval import plan_activity_searches, retrieve_for_module
from app.services.prompts import load_prompt
from app.services.retrieval import extract_youtube_video_id, image_search, video_search
from app.services.vector_store import build_or_update_index
from app.services.vector_store import query as query_vector_store

# Per-activity cap on retrieved document chunks - mirrors module_retrieval.py's
# MAX_RESULTS_PER_ACTIVITY (3) for the web-search path: enough for a
# well-grounded activity without flooding the generation prompt.
MAX_CHUNKS_PER_ACTIVITY = 4

# Tavily has no video-duration field, so a video activity's estimatedMinutes
# is a fixed guess, not a pretense of knowing the real length.
VIDEO_ESTIMATED_MINUTES = 8


@dataclass
class _ActivitySpec:
    """A resolved activity, ready to persist as a real Activity row.

    Bridges GeneratedActivitySchema-based text activities and the
    code-built video activity (which never flows through that schema - see
    _maybe_build_video_spec()) into one uniform shape, so
    generate_module_activities()'s persistence step doesn't need to care
    which path an activity came from.
    """

    type: str
    title: str
    estimated_minutes: int
    content: dict


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

    generated, video_result = _generate_activities_content(module)
    specs = [_generated_to_spec(a) for a in generated]
    if video_result is not None:
        video_spec, position = video_result
        specs.insert(position, video_spec)

    # All available, never locked: a module's activities are generated
    # together in this one call, so there's no such thing as "generated but
    # not reachable yet" for an activity the way there is for a module that
    # hasn't been generated at all.
    activities = [
        Activity(
            id=str(uuid4()),
            position=i,
            activity_type=spec.type,
            title=spec.title,
            status="available",
            estimated_minutes=spec.estimated_minutes,
        )
        for i, spec in enumerate(specs)
    ]

    for activity, spec in zip(activities, specs):
        activity.content_path = save_activity_content(activity.id, spec.content)

    module.activities = activities
    _generate_and_persist_digest(module)
    db.session.commit()
    return module


def _generated_to_spec(a: GeneratedActivitySchema) -> _ActivitySpec:
    return _ActivitySpec(
        type=a.type,
        title=a.title,
        estimated_minutes=a.estimatedMinutes,
        content=a.model_dump(exclude={"type", "title", "estimatedMinutes"}),
    )


def _try_resolve_embedding_config() -> dict | None:
    """Best-effort resolve_embedding_config(): None instead of raising when unconfigured.

    Module generation shouldn't hard-fail just because no embedding model
    is set - grounding falls back to raw source text/search results instead
    (see _generate_activities_content()), same as before the embedding-backed
    RAG rework, just without semantic per-activity relevance ranking.
    """
    try:
        return resolve_embedding_config()
    except EmbeddingNotConfiguredError:
        return None


def _get_module_or_raise(module_id: str) -> Module:
    module = db.session.get(Module, module_id)
    if module is None:
        raise ModuleNotFoundError(f"No module with id '{module_id}'")
    return module


def _generate_activities_content(
    module: Module,
) -> tuple[list[GeneratedActivitySchema], tuple[_ActivitySpec, int] | None]:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_activities(module), None

    model_config = resolve_model_config()
    embedding_config = _try_resolve_embedding_config()
    settings = UserSettings.get_or_create()
    results_by_activity: dict[int, list[dict]] = {}
    citations_by_activity: dict[int, list[CitationSchema]] = {}

    # Video embedding is independent of grounding source (it's never
    # chunked/embedded into the RAG vector store), so the search-plan call
    # needs to run even for a purely document-grounded course that would
    # otherwise skip it entirely - the one case where enabling the toggle
    # adds a genuinely new LLM call, rather than piggybacking on one that
    # was already going to happen.
    needs_search_plan = (
        not module.course.source_materials
        or module.course.web_search_supplement_enabled
        or settings.video_embedding_enabled
    )
    search_plan: ModuleSearchPlanSchema | None = None
    if needs_search_plan:
        search_plan = plan_activity_searches(module, model_config)

    if not module.course.source_materials or module.course.web_search_supplement_enabled:
        # Web-grounded, or a document-grounded course that opted in to
        # supplementing its document(s) with web search (see
        # course_generation.py's _ingest_source_materials()) rather than
        # grounding solely in them - either way, an LLM is still needed to
        # plan good search terms (unlike document/already-fetched-web
        # material, there's no way to query an arbitrary web corpus by
        # embedding alone) - planned unconditionally, even without a Tavily
        # key configured (retrieve_for_module() already returns empty
        # results for every activity in that case).
        search_results = retrieve_for_module(
            module, search_plan, settings.tavily_api_key, settings.deep_search_enabled
        )
        if embedding_config:
            # The fetched content is chunked and embedded into the course's
            # vector index rather than used raw - same storage/retrieval
            # mechanism a document gets, just fed by a fresh Tavily fetch
            # instead of an upload. Guarded by `if web_chunks` so a key-less
            # or empty-results course never pays for an embedding call it
            # doesn't need.
            web_chunks = [
                chunk
                for results in search_results.values()
                for r in results
                for chunk in chunk_pages(r["title"], [(None, r["content"])], url=r["url"])
            ]
            if web_chunks:
                module.course.vector_index_path = build_or_update_index(module.course, web_chunks, embedding_config)
        else:
            # No embedding model configured: ground each activity on its
            # raw fetched results directly, same as before the RAG rework.
            # Still deterministic - retrieve_for_module() already returns
            # results keyed per activity, so citations don't need the model
            # to author them here either, just a lower-quality (unranked by
            # semantic relevance) version of the same grounding.
            results_by_activity = {
                i: [{"source": r["title"], "content": r["content"]} for r in results]
                for i, results in search_results.items()
                if results
            }
            citations_by_activity = {
                i: [CitationSchema(label=r["title"], url=r["url"]) for r in results]
                for i, results in search_results.items()
                if results
            }

    if module.course.vector_index_path and embedding_config:
        # Covers document-grounded, web-grounded, and a supplemented course
        # (both at once - just indexed above if this course had no index
        # yet). One retrieval mechanism regardless of source: the
        # activity's own title+plan, embedded directly, is
        # the query, since there's no need for an LLM to creatively phrase a
        # query against material that's already in hand (either just-fetched
        # or previously uploaded). One batched embedding call for every
        # activity in the module, then fast local FAISS searches - no
        # threading needed, there's no per-activity network I/O here the way
        # Tavily fetches themselves have.
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
    # else: either source materials exist but no index is usable right now
    # (ingested before chunking/embedding was added, embedding failed at
    # ingestion time, or no embedding model is configured at all) - no
    # per-activity chunk retrieval is possible - or this was the no-embedding
    # web branch above, which already populated results_by_activity/
    # citations_by_activity itself. Falls through to
    # _module_seed_data_message()'s own legacy whole-document fallback below
    # instead of leaving these activities completely ungrounded.

    video_result = _maybe_build_video_spec(module, search_plan, model_config, settings)

    use_raw_source_materials = bool(module.course.source_materials) and not (
        module.course.vector_index_path and embedding_config
    )
    messages = [
        {"role": "system", "content": load_prompt("module_activity_generation")},
        {"role": "user", "content": _module_seed_data_message(module, use_raw_source_materials)},
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
        if planned["type"] == "reading":
            if i in citations_by_activity:
                # Deterministic, not model-authored, for both document and
                # web sources now: we already know exactly which chunks were
                # retrieved and handed to this activity, so there's no reason
                # to trust the model to correctly echo back a source/page/url
                # - same reasoning as correctAnswerIndex replacing
                # text-matching for quizzes.
                parsed = parsed.model_copy(update={"citations": citations_by_activity[i]})
            if settings.visual_aids_enabled and settings.tavily_api_key:
                parsed = _add_visual_aids(parsed, model_config, settings.tavily_api_key)
        generated.append(parsed)
        messages.append({"role": "assistant", "content": raw})

    return generated, video_result


def _chunk_citation_label(chunk: Chunk) -> str:
    return f"{chunk.source}, p. {chunk.page}" if chunk.page is not None else chunk.source


def _add_visual_aids(activity: GeneratedActivitySchema, model_config: dict, tavily_api_key: str) -> GeneratedActivitySchema:
    """Splice 0-3 real images into a finished reading activity's body, where they'd clarify a concept.

    Only called when UserSettings.visual_aids_enabled and a Tavily key are
    both set (see the caller). Graceful degradation throughout, matching
    this codebase's existing precedent for imperfect model output (e.g.
    plannedActivities defaulting to []): an aid whose anchorText isn't
    found verbatim in the body (weak-model hallucination), or whose image
    search returns nothing, is silently skipped rather than erroring -
    zero spliced images is a completely normal outcome, not a failure.

    Args:
        activity: The already-generated reading activity.
        model_config: Resolved completion model settings.
        tavily_api_key: The learner's Tavily API key.

    Returns:
        The activity, with 0+ images spliced into its body as
        `![caption](url)` right after each successfully-matched aid's
        anchor text. Unchanged (same object) if body is empty or no aid
        could be placed.
    """
    if not activity.body:
        return activity

    plan = _plan_visual_aids(activity.body, model_config)
    body = activity.body
    for aid in plan.aids:
        if aid.anchorText not in body:
            continue
        images = image_search(aid.query, tavily_api_key)
        if not images or not images[0]["url"]:
            continue
        body = body.replace(aid.anchorText, f"{aid.anchorText}\n\n![{aid.caption}]({images[0]['url']})", 1)

    if body == activity.body:
        return activity
    return activity.model_copy(update={"body": body})


def _plan_visual_aids(body: str, model_config: dict) -> VisualAidPlanSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return VisualAidPlanSchema(aids=[])

    messages = [
        {"role": "system", "content": load_prompt("lesson_visual_aids")},
        {"role": "user", "content": body},
    ]
    raw = complete(messages=messages, schema=VisualAidPlanSchema, **model_config)
    return validate_llm_json(raw, VisualAidPlanSchema)


def _maybe_build_video_spec(
    module: Module,
    search_plan: ModuleSearchPlanSchema | None,
    model_config: dict,
    settings: UserSettings,
) -> tuple[_ActivitySpec, int] | None:
    """Best-effort: find and select one relevant YouTube video for this module.

    Only attempted when UserSettings.video_embedding_enabled and a Tavily
    key are both set, and the search-plan call actually suggested a query
    (see ModuleSearchPlanSchema.videoSearchQuery) - most modules won't get
    one, which is the intended "try to include, don't force it" behavior,
    not a degraded case. Graceful degradation throughout, same precedent as
    _add_visual_aids(): no candidate with a real parseable video id, or the
    model declining every candidate, just means no video this module, not
    an error.

    Args:
        module: The module being generated.
        search_plan: The module's search plan, or None if it was never
            computed (video embedding off and this course didn't otherwise
            need one - see _generate_activities_content()).
        model_config: Resolved completion model settings.
        settings: The learner's current UserSettings row.

    Returns:
        A (spec, position) pair, where position is the 0-based index (in
        the module's final activity list) to insert the video at, clamped
        to a valid range - or None if no video should be added.
    """
    if search_plan is None or not settings.video_embedding_enabled or not settings.tavily_api_key:
        return None
    if not search_plan.videoSearchQuery:
        return None

    candidates = [
        c
        for c in video_search(search_plan.videoSearchQuery, settings.tavily_api_key)
        if extract_youtube_video_id(c["url"])
    ]
    if not candidates:
        return None

    selection = _select_video(candidates, module, model_config)
    if not (0 <= selection.selectedIndex < len(candidates)):
        return None

    chosen = candidates[selection.selectedIndex]
    video_id = extract_youtube_video_id(chosen["url"])
    spec = _ActivitySpec(
        type="video",
        title=chosen["title"] or "Watch this video",
        estimated_minutes=VIDEO_ESTIMATED_MINUTES,
        content={"videoUrl": chosen["url"], "videoId": video_id, "caption": selection.caption},
    )
    position = max(0, min(search_plan.videoPosition, len(module.activity_plan)))
    return spec, position


def _select_video(candidates: list[dict], module: Module, model_config: dict) -> VideoSelectionSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return VideoSelectionSchema(selectedIndex=-1, caption="")

    messages = [
        {"role": "system", "content": load_prompt("module_video_selection")},
        {"role": "user", "content": _video_selection_data_message(module, candidates)},
    ]
    raw = complete(messages=messages, schema=VideoSelectionSchema, **model_config)
    return validate_llm_json(raw, VideoSelectionSchema)


def _video_selection_data_message(module: Module, candidates: list[dict]) -> str:
    candidate_lines = "\n".join(f"{i}. {c['title']}: {c['content']}" for i, c in enumerate(candidates))
    return f"Module: {module.title}\n{module.description}\n\nCandidate videos:\n{candidate_lines}"


def _module_seed_data_message(module: Module, use_raw_source_materials: bool) -> str:
    outcomes = "\n".join(f"- {outcome}" for outcome in module.learning_outcomes)
    parts = [
        assemble_learning_history(module.course),
        f"Module: {module.title}\n{module.description}",
        f"This module's learning outcomes:\n{outcomes}",
        f"The full planned sequence of activities for this module:\n{_format_activity_plan(module.activity_plan)}",
    ]
    if use_raw_source_materials:
        # Legacy/no-embedding fallback: see _generate_activities_content()'s
        # matching comment - reached when no chunk-retrieval index is
        # usable for this call (never built, ingested before
        # chunking/embedding existed, or no embedding model is currently
        # configured). Whole-document-in-one-block is worse for large
        # documents (see this module's docstring) but strictly better than
        # no grounding at all.
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
        # "caption" covers a video activity, which has neither body/prompt/
        # question - see _maybe_build_video_spec()'s content shape.
        text = content.get("body") or content.get("prompt") or content.get("question") or content.get("caption") or ""
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
            checkPrompt=f"[MOCK] What's the key idea behind {planned['title']}?",
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
