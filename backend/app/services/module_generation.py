"""Generates a module's learning activities.

Per docs/course_creation_websearch_flow.md: a module's activities were
already planned at outline time (see course_generation.py's Module.activity_plan),
so generation's job is to search for material and write content for each
one, not invent them from scratch. Search happens deliberately, up front,
for the whole module (see module_retrieval.py) rather than being left to a
model-driven tool-calling loop. Activities are then generated one at a
time as a running chat history, so each one's content has real continuity
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
by capping history size or configuring a larger context window.
"""

from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import Activity, ConversationMessage, Module, UserSettings
from app.services.content_storage import save_activity_content
from app.services.course_context import assemble_learning_history, render_source_materials
from app.services.llm import complete
from app.services.llm_schemas import CitationSchema, GeneratedActivitySchema, ModuleDigestSchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.module_retrieval import plan_activity_searches, retrieve_for_module
from app.services.prompts import load_prompt


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
    if module.course.source_materials:
        # Document-grounded: the learner's own uploaded material is the
        # source of truth for this course, so search is skipped entirely
        # rather than searching the web alongside it (per
        # docs/course_creation_websearch_flow.md: "no websearch is needed,
        # just the document text"). The document's text goes into the seed
        # prompt below instead.
        search_results: dict[int, list[dict]] = {}
    else:
        settings = UserSettings.get_or_create()
        search_plan = plan_activity_searches(module, model_config)
        search_results = retrieve_for_module(
            module, search_plan, settings.tavily_api_key, settings.deep_search_enabled
        )

    messages = [
        {"role": "system", "content": load_prompt("module_activity_generation")},
        {"role": "user", "content": _module_seed_data_message(module)},
    ]
    generated: list[GeneratedActivitySchema] = []
    for i, planned in enumerate(module.activity_plan):
        turn = _activity_turn_message(i, module.activity_plan, planned, search_results.get(i, []))
        messages.append({"role": "user", "content": turn})
        raw = complete(messages=messages, schema=GeneratedActivitySchema, **model_config)
        generated.append(validate_llm_json(raw, GeneratedActivitySchema))
        messages.append({"role": "assistant", "content": raw})

    return generated


def _module_seed_data_message(module: Module) -> str:
    outcomes = "\n".join(f"- {outcome}" for outcome in module.learning_outcomes)
    parts = [
        assemble_learning_history(module.course),
        f"Module: {module.title}\n{module.description}",
        f"This module's learning outcomes:\n{outcomes}",
        f"The full planned sequence of activities for this module:\n{_format_activity_plan(module.activity_plan)}",
    ]
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
        lines.append("Search results to ground this activity in:")
        lines.extend(f"- {r['title']} ({r['url']}): {r['content']}" for r in results)
    else:
        lines.append(
            "No search results are available for this activity; ground it in any source materials "
            "provided above, or rely on your own knowledge if none were provided."
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
    )
