"""Tests for estimate_costs.py's pure average-course extrapolation, rendering, and path logic.

Doesn't touch the DB or a real/mocked LLM - run() (the actual end-to-end
drive) is a manual tool, not something the automated suite exercises.
"""

from pathlib import Path

from estimate_costs import (
    DEFAULT_OUTPUT_FILENAME,
    REPO_ROOT,
    _render_report,
    _resolve_output_path,
    estimate_average_course_tokens,
)
from app.services.llm_pricing import REFERENCE_MODELS


def _group(call_type: str, calls: int, prompt: int, completion: int) -> dict:
    return {
        "callType": call_type,
        "totalCalls": calls,
        "promptTokens": prompt,
        "completionTokens": completion,
        "totalTokens": prompt + completion,
    }


def _fake_summary() -> dict:
    # 2 modules sampled, 4 activities sampled (2 per module) across those modules.
    return {
        "byCallType": [
            _group("interview_question", 5, 500, 100),
            _group("course_outline", 1, 100, 20),
            _group("search_terms_planning", 2, 200, 40),
            _group("module_digest", 2, 100, 20),
            _group("module_activity", 4, 800, 160),
            _group("activity_feedback", 1, 50, 10),
        ],
    }


def test_estimate_average_course_tokens_scales_by_assumed_course_shape() -> None:
    prompt_tokens, completion_tokens = estimate_average_course_tokens(
        _fake_summary(), modules_sampled=2, avg_modules=5, avg_activities_per_module=3
    )

    # course-level (600, 120) + 5 modules * (per-module (150, 30) + 3 activities * per-activity (200, 40))
    assert prompt_tokens == 4350
    assert completion_tokens == 870


def test_estimate_average_course_tokens_excludes_activity_feedback() -> None:
    with_feedback = estimate_average_course_tokens(_fake_summary(), 2, 5, 3)

    summary_without_feedback = _fake_summary()
    summary_without_feedback["byCallType"] = [
        g for g in summary_without_feedback["byCallType"] if g["callType"] != "activity_feedback"
    ]
    without_feedback = estimate_average_course_tokens(summary_without_feedback, 2, 5, 3)

    assert with_feedback == without_feedback


def test_estimate_average_course_tokens_handles_no_modules_sampled() -> None:
    summary = {"byCallType": [_group("course_outline", 1, 100, 20)]}

    prompt_tokens, completion_tokens = estimate_average_course_tokens(summary, modules_sampled=0, avg_modules=5, avg_activities_per_module=3)

    assert prompt_tokens == 100
    assert completion_tokens == 20


def test_render_report_lists_assumptions_and_reference_model_costs() -> None:
    report = _render_report(_fake_summary(), modules_sampled=2, avg_modules=5, avg_activities_per_module=3)

    assert "## Assumptions" in report
    assert "**5 modules**" in report
    assert "**3 activities**" in report
    assert "## Estimated cost of generating an average course" in report
    for name in REFERENCE_MODELS:
        assert f"| {name} |" in report


def test_render_report_omits_the_old_per_call_breakdown() -> None:
    report = _render_report(_fake_summary(), modules_sampled=2, avg_modules=5, avg_activities_per_module=3)

    assert "Breakdown by generation step" not in report
    assert "Breakdown by content type" not in report


def test_resolve_output_path_joins_a_relative_filename_onto_the_repo_root() -> None:
    resolved = _resolve_output_path(DEFAULT_OUTPUT_FILENAME)

    assert resolved == REPO_ROOT / DEFAULT_OUTPUT_FILENAME


def test_resolve_output_path_leaves_an_absolute_path_unchanged() -> None:
    absolute = Path("/tmp/some-report.md")

    assert _resolve_output_path(str(absolute)) == absolute


def test_default_output_filename_is_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()

    assert DEFAULT_OUTPUT_FILENAME in gitignore.splitlines()
