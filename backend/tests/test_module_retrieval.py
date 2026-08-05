"""Tests for per-module search-term planning and retrieval.

Search planning runs one LLM call per module (not per activity, so the
model can avoid redundant queries across activities), then retrieval
executes deterministically off that plan — no more model deciding for
itself what to search, unlike the old run_agent tool-calling approach (see
docs/course_creation_websearch_flow.md).
"""

import time

import pytest

from app.extensions import db as _db
from app.models import Course, Module
from app.services.llm_schemas import ActivitySearchPlanSchema, LLMOutputValidationError, ModuleSearchPlanSchema
from app.services.module_retrieval import plan_activity_searches, retrieve_for_module


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _make_module(activity_plan=None) -> Module:
    course = Course(
        id="c1", title="GPU Programming", description="A practical intro.", prerequisites=[],
        estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
    )
    module = Module(
        id="m1", course_id="c1", position=0, title="Getting Started", description="Foundational concepts.",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=["Understand the basics"],
        activity_plan=activity_plan or [
            {"type": "reading", "title": "What Is a GPU?", "plan": "Cover the basics."},
            {"type": "assessment", "title": "Check Understanding", "plan": "Quiz the basics."},
        ],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_plan_activity_searches_mock_covers_every_activity_index(db) -> None:
    module = _make_module()

    plan = plan_activity_searches(module, model_config={"model": "test"})

    assert {a.activityIndex for a in plan.activities} == {0, 1}


def test_plan_activity_searches_mock_never_suggests_a_video(db) -> None:
    module = _make_module()

    plan = plan_activity_searches(module, model_config={"model": "test"})

    assert plan.videoSearchQuery == ""
    assert plan.videoPosition == 0


def test_plan_activity_searches_parses_video_fields_from_real_response(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse(
                '{"activities": [{"activityIndex": 0, "terms": []}, {"activityIndex": 1, "terms": []}], '
                '"videoSearchQuery": "GPU warp scheduling explained", "videoPosition": 1}'
            ),
        )

        plan = plan_activity_searches(module, model_config={"model": "test"})

        assert plan.videoSearchQuery == "GPU warp scheduling explained"
        assert plan.videoPosition == 1


def test_plan_activity_searches_parses_real_response(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse(
                '{"activities": [{"activityIndex": 0, "terms": ["GPU basics"]}, '
                '{"activityIndex": 1, "terms": []}], '
                '"videoSearchQuery": "", "videoPosition": 0}'
            ),
        )

        plan = plan_activity_searches(module, model_config={"model": "test"})

        assert plan.activities[0].terms == ["GPU basics"]
        assert plan.activities[1].terms == []


def test_plan_activity_searches_raises_when_an_activity_index_is_missing(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse(
                '{"activities": [{"activityIndex": 0, "terms": ["GPU basics"]}], '
                '"videoSearchQuery": "", "videoPosition": 0}'
            ),
        )

        with pytest.raises(LLMOutputValidationError):
            plan_activity_searches(module, model_config={"model": "test"})


def test_plan_activity_searches_raises_for_out_of_range_index(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse(
                '{"activities": [{"activityIndex": 0, "terms": []}, {"activityIndex": 5, "terms": []}], '
                '"videoSearchQuery": "", "videoPosition": 0}'
            ),
        )

        with pytest.raises(LLMOutputValidationError):
            plan_activity_searches(module, model_config={"model": "test"})


def test_retrieve_for_module_returns_empty_results_without_tavily_key(db) -> None:
    module = _make_module()
    plan = plan_activity_searches(module, model_config={"model": "test"})

    results = retrieve_for_module(module, plan, tavily_api_key=None, deep_search=False)

    assert results == {0: [], 1: []}


def test_retrieve_for_module_returns_results_per_activity_with_tavily_key(db) -> None:
    module = _make_module()
    plan = plan_activity_searches(module, model_config={"model": "test"})

    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)

    assert len(results[0]) >= 1
    assert all({"title", "url", "content"} <= r.keys() for r in results[0])


def test_retrieve_for_module_dedupes_results_by_url(db, monkeypatch) -> None:
    module = _make_module(activity_plan=[{"type": "reading", "title": "T", "plan": "p"}])
    plan = ModuleSearchPlanSchema(
        activities=[ActivitySearchPlanSchema(activityIndex=0, terms=["term a", "term b"])],
        videoSearchQuery="",
        videoPosition=0,
    )

    monkeypatch.setattr(
        "app.services.module_retrieval.web_search",
        lambda query, api_key, search_depth="basic": [
            {"title": "Same Result", "url": "https://example.com/dup", "content": "c"}
        ],
    )

    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)

    assert len(results[0]) == 1


def test_retrieve_for_module_caps_results_per_activity(db, monkeypatch) -> None:
    module = _make_module(activity_plan=[{"type": "reading", "title": "T", "plan": "p"}])
    plan = ModuleSearchPlanSchema(
        activities=[ActivitySearchPlanSchema(activityIndex=0, terms=["a", "b", "c"])],
        videoSearchQuery="",
        videoPosition=0,
    )

    monkeypatch.setattr(
        "app.services.module_retrieval.web_search",
        lambda query, api_key, search_depth="basic": [
            {"title": f"{query} 1", "url": f"https://example.com/{query}-1", "content": "c"},
            {"title": f"{query} 2", "url": f"https://example.com/{query}-2", "content": "c"},
        ],
    )

    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)

    assert len(results[0]) == 3


def test_retrieve_for_module_passes_deep_search_flag_as_search_depth(db, monkeypatch) -> None:
    module = _make_module(activity_plan=[{"type": "reading", "title": "T", "plan": "p"}])
    plan = ModuleSearchPlanSchema(
        activities=[ActivitySearchPlanSchema(activityIndex=0, terms=["a"])],
        videoSearchQuery="",
        videoPosition=0,
    )
    captured: dict = {}

    def fake_web_search(query, api_key, search_depth="basic"):
        captured["search_depth"] = search_depth
        return []

    monkeypatch.setattr("app.services.module_retrieval.web_search", fake_web_search)

    retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=True)

    assert captured["search_depth"] == "advanced"


def test_retrieve_for_module_gives_empty_list_to_activity_with_no_search_terms(db) -> None:
    module = _make_module(activity_plan=[{"type": "discussion", "title": "T", "plan": "p"}])
    plan = ModuleSearchPlanSchema(
        activities=[ActivitySearchPlanSchema(activityIndex=0, terms=[])],
        videoSearchQuery="",
        videoPosition=0,
    )

    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)

    assert results[0] == []


def test_retrieve_for_module_returns_empty_dict_for_empty_search_plan(db) -> None:
    module = _make_module()
    plan = ModuleSearchPlanSchema(activities=[], videoSearchQuery="", videoPosition=0)

    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)

    assert results == {}


def test_retrieve_for_module_searches_activities_concurrently(db, monkeypatch) -> None:
    # Each activity's search is independent (its own Tavily calls), so they
    # should run in a thread pool rather than one after another. If they
    # were still sequential, 3 activities x a 0.2s search each would take
    # >= 0.6s; concurrently, wall time should stay well under that.
    module = _make_module(
        activity_plan=[
            {"type": "reading", "title": "A", "plan": "p"},
            {"type": "reading", "title": "B", "plan": "p"},
            {"type": "reading", "title": "C", "plan": "p"},
        ]
    )
    plan = ModuleSearchPlanSchema(
        activities=[
            ActivitySearchPlanSchema(activityIndex=0, terms=["a"]),
            ActivitySearchPlanSchema(activityIndex=1, terms=["b"]),
            ActivitySearchPlanSchema(activityIndex=2, terms=["c"]),
        ],
        videoSearchQuery="",
        videoPosition=0,
    )

    def slow_web_search(query, api_key, search_depth="basic"):
        time.sleep(0.2)
        return [{"title": query, "url": f"https://example.com/{query}", "content": "c"}]

    monkeypatch.setattr("app.services.module_retrieval.web_search", slow_web_search)

    start = time.monotonic()
    results = retrieve_for_module(module, plan, tavily_api_key="tvly-test", deep_search=False)
    elapsed = time.monotonic() - start

    assert len(results) == 3
    assert elapsed < 0.5
