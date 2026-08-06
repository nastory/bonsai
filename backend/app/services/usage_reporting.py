"""Aggregates logged LLM token usage (see app/models.py's LLMUsageLog) into a cost report.

One course, or every course, grouped by module, content type (reading/quiz/
essay/...), and call type (interview_question/course_outline/...) - each
group and the grand total also carry an estimated hypothetical dollar cost
under every app/services/llm_pricing.py reference model.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable

from app.extensions import db
from app.models import Course, LLMUsageLog, Module
from app.services.llm_pricing import REFERENCE_MODELS, estimate_cost


def summarize_usage(course_id: str | None = None) -> dict:
    """Aggregate logged LLM usage, optionally scoped to one course.

    Args:
        course_id: If given, only this course's usage is included. If
            None, every course's usage is aggregated together, and the
            result also breaks totals down by course.

    Returns:
        A dict with grand totals (tokens, call count, estimated cost per
        reference model), plus breakdowns by content type, call type, and
        module - and by course too, when course_id is None.
    """
    query = db.select(LLMUsageLog)
    if course_id is not None:
        query = query.where(LLMUsageLog.course_id == course_id)
    rows = list(db.session.execute(query).scalars())

    result = {
        "courseId": course_id,
        **_totals(rows),
        "byContentType": _group_by(
            [r for r in rows if r.content_type is not None], lambda r: r.content_type, "contentType"
        ),
        "byCallType": _group_by(rows, lambda r: r.call_type, "callType"),
        "byModule": _group_by_module([r for r in rows if r.module_id is not None]),
    }
    if course_id is None:
        result["byCourse"] = _group_by_course([r for r in rows if r.course_id is not None])
    return result


def _totals(rows: list[LLMUsageLog]) -> dict:
    prompt_tokens = sum(r.prompt_tokens for r in rows)
    completion_tokens = sum(r.completion_tokens for r in rows)
    return {
        "totalCalls": len(rows),
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "totalTokens": prompt_tokens + completion_tokens,
        "estimatedCostUsd": _cost_breakdown(prompt_tokens, completion_tokens),
    }


def _cost_breakdown(prompt_tokens: int, completion_tokens: int) -> dict[str, float | None]:
    """Estimated cost under every REFERENCE_MODELS entry, keyed by display name."""
    return {
        name: estimate_cost(prompt_tokens, completion_tokens, key) for name, key in REFERENCE_MODELS.items()
    }


def _group_by(rows: Iterable[LLMUsageLog], key_fn: Callable[[LLMUsageLog], str], key_field: str) -> list[dict]:
    groups: dict[str, list[LLMUsageLog]] = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)

    breakdown = [{key_field: key, **_totals(group_rows)} for key, group_rows in groups.items()]
    breakdown.sort(key=lambda g: g["totalTokens"], reverse=True)
    return breakdown


def _group_by_module(rows: list[LLMUsageLog]) -> list[dict]:
    module_ids = {r.module_id for r in rows}
    id_and_title = db.select(Module.id, Module.title).where(Module.id.in_(module_ids))
    titles = {row.id: row.title for row in db.session.execute(id_and_title)}

    groups: dict[str, list[LLMUsageLog]] = defaultdict(list)
    for row in rows:
        groups[row.module_id].append(row)

    breakdown = [
        {"moduleId": module_id, "moduleTitle": titles.get(module_id), **_totals(group_rows)}
        for module_id, group_rows in groups.items()
    ]
    breakdown.sort(key=lambda g: g["totalTokens"], reverse=True)
    return breakdown


def _group_by_course(rows: list[LLMUsageLog]) -> list[dict]:
    course_ids = {r.course_id for r in rows}
    id_and_title = db.select(Course.id, Course.title).where(Course.id.in_(course_ids))
    titles = {row.id: row.title for row in db.session.execute(id_and_title)}

    groups: dict[str, list[LLMUsageLog]] = defaultdict(list)
    for row in rows:
        groups[row.course_id].append(row)

    breakdown = [
        {"courseId": course_id, "courseTitle": titles.get(course_id), **_totals(group_rows)}
        for course_id, group_rows in groups.items()
    ]
    breakdown.sort(key=lambda g: g["totalTokens"], reverse=True)
    return breakdown
