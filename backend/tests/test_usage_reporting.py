"""Tests for aggregating LLMUsageLog rows into a cost report."""

from app.extensions import db as _db
from app.models import Course, LLMUsageLog, Module
from app.services.llm_pricing import REFERENCE_MODELS
from app.services.usage_reporting import summarize_usage


def _seed_course(course_id: str, title: str) -> Course:
    course = Course(
        id=course_id, title=title, description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x"
    )
    _db.session.add(course)
    return course


def _seed_module(module_id: str, course_id: str, title: str) -> Module:
    module = Module(
        id=module_id,
        course_id=course_id,
        position=0,
        title=title,
        description="d",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=[],
    )
    _db.session.add(module)
    return module


def _log(
    course_id: str | None,
    module_id: str | None,
    call_type: str,
    content_type: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    _db.session.add(
        LLMUsageLog(
            course_id=course_id,
            module_id=module_id,
            call_type=call_type,
            content_type=content_type,
            model="claude-3-5-sonnet-20241022",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    )


def test_summarize_usage_totals_tokens_for_one_course(db) -> None:
    _seed_course("c1", "Course One")
    _log("c1", None, "course_outline", None, 100, 20)
    _log("c1", None, "interview_question", None, 50, 10)
    _db.session.commit()

    summary = summarize_usage("c1")

    assert summary["courseId"] == "c1"
    assert summary["totalCalls"] == 2
    assert summary["promptTokens"] == 150
    assert summary["completionTokens"] == 30
    assert summary["totalTokens"] == 180


def test_summarize_usage_scoped_to_a_course_excludes_other_courses(db) -> None:
    _seed_course("c1", "Course One")
    _seed_course("c2", "Course Two")
    _log("c1", None, "course_outline", None, 100, 20)
    _log("c2", None, "course_outline", None, 999, 999)
    _db.session.commit()

    summary = summarize_usage("c1")

    assert summary["totalTokens"] == 120


def test_summarize_usage_groups_by_content_type(db) -> None:
    _seed_course("c1", "Course One")
    _seed_module("m1", "c1", "Module One")
    _log("c1", "m1", "module_activity", "reading", 100, 20)
    _log("c1", "m1", "module_activity", "reading", 50, 10)
    _log("c1", "m1", "module_activity", "quiz", 30, 5)
    _log("c1", None, "course_outline", None, 200, 40)  # no content_type - excluded
    _db.session.commit()

    summary = summarize_usage("c1")
    by_type = {g["contentType"]: g for g in summary["byContentType"]}

    assert by_type["reading"]["totalTokens"] == 180
    assert by_type["reading"]["totalCalls"] == 2
    assert by_type["quiz"]["totalTokens"] == 35
    assert set(by_type) == {"reading", "quiz"}


def test_summarize_usage_groups_by_call_type_and_module(db) -> None:
    _seed_course("c1", "Course One")
    _seed_module("m1", "c1", "Module One")
    _log("c1", "m1", "module_activity", "reading", 100, 20)
    _log("c1", None, "course_outline", None, 50, 10)
    _db.session.commit()

    summary = summarize_usage("c1")
    by_call = {g["callType"]: g for g in summary["byCallType"]}

    assert by_call["module_activity"]["totalTokens"] == 120
    assert by_call["course_outline"]["totalTokens"] == 60

    assert len(summary["byModule"]) == 1
    assert summary["byModule"][0]["moduleId"] == "m1"
    assert summary["byModule"][0]["moduleTitle"] == "Module One"
    assert summary["byModule"][0]["totalTokens"] == 120


def test_summarize_usage_includes_estimated_cost_for_every_reference_model(db) -> None:
    _seed_course("c1", "Course One")
    _log("c1", None, "course_outline", None, 1_000_000, 1_000_000)
    _db.session.commit()

    summary = summarize_usage("c1")

    assert set(summary["estimatedCostUsd"]) == set(REFERENCE_MODELS)
    assert all(cost is not None and cost > 0 for cost in summary["estimatedCostUsd"].values())


def test_summarize_usage_without_course_id_aggregates_everything_and_breaks_down_by_course(db) -> None:
    _seed_course("c1", "Course One")
    _seed_course("c2", "Course Two")
    _log("c1", None, "course_outline", None, 100, 20)
    _log("c2", None, "course_outline", None, 50, 10)
    _db.session.commit()

    summary = summarize_usage()

    assert summary["courseId"] is None
    assert summary["totalTokens"] == 180
    by_course = {g["courseId"]: g for g in summary["byCourse"]}
    assert by_course["c1"]["courseTitle"] == "Course One"
    assert by_course["c1"]["totalTokens"] == 120
    assert by_course["c2"]["totalTokens"] == 60


def test_summarize_usage_with_no_rows_returns_zeroed_totals(db) -> None:
    summary = summarize_usage("nonexistent")

    assert summary["totalCalls"] == 0
    assert summary["totalTokens"] == 0
    assert summary["byContentType"] == []
    assert summary["byCallType"] == []
    assert summary["byModule"] == []
