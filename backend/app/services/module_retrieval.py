"""Per-module search-term planning and retrieval, run once before any activity content is generated.

Per docs/course_creation_websearch_flow.md: rather than letting the model
decide for itself whether/what to search (the old run_agent tool-calling
approach), module generation now plans search terms for every activity up
front, then retrieves for all of them before writing any content. Keeps
search deliberate and auditable instead of implicit in a tool-call loop.
"""

from concurrent.futures import ThreadPoolExecutor

from flask import current_app

from app.models import Module
from app.services.course_context import assemble_learning_history
from app.services.llm import complete
from app.services.llm_schemas import (
    ActivitySearchPlanSchema,
    LLMOutputValidationError,
    ModuleSearchPlanSchema,
    validate_llm_json,
)
from app.services.prompts import load_prompt
from app.services.retrieval import web_search

# Per-activity caps: enough for a well-grounded activity without either
# spending unbounded Tavily credits or flooding the generation prompt.
MAX_TERMS_PER_ACTIVITY = 3
MAX_RESULTS_PER_ACTIVITY = 3


def plan_activity_searches(module: Module, model_config: dict) -> ModuleSearchPlanSchema:
    """Plan search terms for every activity in a module, in one call.

    The model sees the whole activity_plan at once (rather than one call per
    activity), so it can avoid redundant queries across activities and
    reason about how they relate.

    Args:
        module: The module, with its activity_plan already populated.
        model_config: kwargs for the completion call, from resolve_model_config().

    Returns:
        The search plan, with exactly one entry per planned activity.

    Raises:
        LLMOutputValidationError: If the response doesn't cover every planned
            activity's index exactly once.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        plan = _mock_search_plan(module)
    else:
        messages = [
            {"role": "system", "content": load_prompt("module_search_terms")},
            {"role": "user", "content": _search_planning_data_message(module)},
        ]
        raw = complete(
            messages=messages,
            schema=ModuleSearchPlanSchema,
            course_id=module.course_id,
            module_id=module.id,
            call_type="search_terms_planning",
            **model_config,
        )
        plan = validate_llm_json(raw, ModuleSearchPlanSchema)

    expected_indices = set(range(len(module.activity_plan)))
    actual_indices = {a.activityIndex for a in plan.activities}
    if actual_indices != expected_indices:
        raise LLMOutputValidationError(
            f"Search plan covered activity indices {sorted(actual_indices)}, expected {sorted(expected_indices)}"
        )
    return plan


def retrieve_for_module(
    module: Module, search_plan: ModuleSearchPlanSchema, tavily_api_key: str | None, deep_search: bool
) -> dict[int, list[dict]]:
    """Retrieve search results for every activity in a module's search plan.

    Each activity's searches are independent of every other activity's, so
    they run concurrently in a thread pool: these are network calls to
    Tavily, not CPU work, so real wall-clock time is saved despite the GIL.
    Within one activity, terms are still searched in order with an early
    stop once MAX_RESULTS_PER_ACTIVITY is reached, so this doesn't spend any
    more Tavily credits than the sequential version did.

    Args:
        module: The module being generated.
        search_plan: The per-activity search terms from plan_activity_searches().
        tavily_api_key: The learner's Tavily API key, or None if not configured.
        deep_search: Whether to use Tavily's "advanced" search depth.

    Returns:
        A dict mapping each activity's index to its (deduped, capped) list of
        {"title", "url", "content"} results. An activity with no search
        terms, or when no Tavily key is configured, maps to an empty list.
    """
    if not tavily_api_key or not search_plan.activities:
        return {a.activityIndex: [] for a in search_plan.activities}

    search_depth = "advanced" if deep_search else "basic"
    # current_app is a context-local proxy, not shared automatically across
    # threads: each worker below has to push its own app context (via the
    # captured real app object) before anything it calls can read
    # current_app.config (LLM_TEST_MODE), same as any Flask code run off the
    # request thread.
    app = current_app._get_current_object()

    def _worker(activity_plan: ActivitySearchPlanSchema) -> tuple[int, list[dict]]:
        with app.app_context():
            return activity_plan.activityIndex, _retrieve_for_activity(activity_plan.terms, tavily_api_key, search_depth)

    with ThreadPoolExecutor(max_workers=len(search_plan.activities)) as executor:
        return dict(executor.map(_worker, search_plan.activities))


def _retrieve_for_activity(terms: list[str], tavily_api_key: str, search_depth: str) -> list[dict]:
    seen_urls: set[str] = set()
    results: list[dict] = []
    for term in terms[:MAX_TERMS_PER_ACTIVITY]:
        if len(results) >= MAX_RESULTS_PER_ACTIVITY:
            break
        for result in web_search(term, tavily_api_key, search_depth=search_depth):
            if result["url"] in seen_urls:
                continue
            seen_urls.add(result["url"])
            results.append(result)
            if len(results) >= MAX_RESULTS_PER_ACTIVITY:
                break
    return results


def _search_planning_data_message(module: Module) -> str:
    parts = [
        assemble_learning_history(module.course),
        f"Module: {module.title}\n{module.description}",
        f"Planned activities:\n{_format_activity_plan(module)}",
    ]
    return "\n\n".join(p for p in parts if p)


def _format_activity_plan(module: Module) -> str:
    return "\n".join(
        f"{i}. [{a['type']}] {a['title']}: {a['plan']}" for i, a in enumerate(module.activity_plan)
    )


def _mock_search_plan(module: Module) -> ModuleSearchPlanSchema:
    return ModuleSearchPlanSchema(
        activities=[
            ActivitySearchPlanSchema(activityIndex=i, terms=[f"[MOCK] {a['title']}"])
            for i, a in enumerate(module.activity_plan)
        ],
        # Mocks never suggest a video - kept deterministic and free, same as
        # every other LLM_TEST_MODE branch in this codebase.
        videoSearchQuery="",
        videoPosition=0,
    )
