"""Run one realistic dummy course through real generation and estimate an average course's cost.

Drives the real course-creation -> outline -> module-generation -> feedback
-> discussion flow (no HTTP, no mocking - LLM_TEST_MODE stays off) against a throwaway
in-memory database, measures real per-call token usage, then extrapolates
to an assumed-size "average" course (see AVG_MODULES_PER_COURSE/
AVG_ACTIVITIES_PER_MODULE below, overridable via CLI) and prints each
reference model's pricing plus its estimated cost for that average course.
Never touches the README itself - copy the output in yourself, if you want
it there. Pass --output-file to also save it to a file (gitignored by
default - see .gitignore) instead of only printing it.

Defaults to a free local Ollama model (BYOM), so this can be run for the
cost of nothing but time - see model_selection.py's DEFAULT_BYOM_MODEL/
DEFAULT_BYOM_ENDPOINT. Generating several modules against a local model can
take a few minutes; the resulting estimate depends on both what the model
actually generates and the size assumptions below, so treat it as
illustrative, not a guarantee of what a real course would cost.

Requires a running Ollama with the chosen model pulled (`ollama pull llama3`
for the default). Run with: python estimate_costs.py
"""

import argparse
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Activity, Course, UserSettings
from app.services.activity_feedback import generate_activity_feedback
from app.services.course_generation import approve_outline, generate_outline, start_course, submit_interview_answer
from app.services.discussion import MAX_DISCUSSION_TURNS, generate_discussion_reply
from app.services.llm_pricing import REFERENCE_MODELS, estimate_cost, rate_per_million_tokens
from app.services.model_selection import DEFAULT_BYOM_ENDPOINT, DEFAULT_BYOM_MODEL
from app.services.module_generation import generate_module_activities
from app.services.usage_reporting import summarize_usage

# This file lives at <repo root>/backend/estimate_costs.py.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_FILENAME = "cost_estimate.md"

DEFAULT_TOPIC = "the basics of how a car engine works"
DUMMY_ANSWER = "I'm a complete beginner and want a practical, hands-on introduction I can work through in a couple of weeks."
DUMMY_FEEDBACK_RESPONSE = "This is a dummy learner response, written only to sample activity-feedback generation."

# Reasonable defaults for an "average" course's shape, overridable via CLI.
# Roughly matches this repo's own example courses (see seed.py): most
# modules there plan 3-4 activities (reading(s) + a project/quiz +
# an assessment).
AVG_MODULES_PER_COURSE = 5
AVG_ACTIVITIES_PER_MODULE = 4

# call_type -> which unit of an "average course" it scales with. Anything
# not listed here (activity_feedback, document_summary) is excluded from
# the average-course estimate: both are on-demand/conditional (a learner's
# free-text submission, a document-grounded course's upload) rather than
# part of generating the course itself.
COURSE_LEVEL_CALL_TYPES = {"interview_question", "course_outline", "course_context_compaction"}
PER_MODULE_CALL_TYPES = {"search_terms_planning", "module_digest", "video_selection"}
PER_ACTIVITY_CALL_TYPES = {"module_activity", "visual_aid_plan"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="What the dummy course should be about.")
    parser.add_argument(
        "--modules", default="2", help='How many modules to generate content for: a number, or "all" (default: 2).'
    )
    parser.add_argument("--byom-model", default=DEFAULT_BYOM_MODEL, help="Local Ollama model to use (default: llama3).")
    parser.add_argument(
        "--byom-endpoint", default=DEFAULT_BYOM_ENDPOINT, help="Local Ollama endpoint (default: http://localhost:11434)."
    )
    parser.add_argument(
        "--provider", choices=["anthropic", "openai"], help="Use a real hosted provider instead of local BYOM."
    )
    parser.add_argument("--hosted-model", help="Hosted model id to call (requires --provider).")
    parser.add_argument("--api-key", help="Hosted provider API key (requires --provider).")
    parser.add_argument(
        "--tavily-key", help="Optional Tavily key - also samples visual-aid/video-embedding generation calls."
    )
    parser.add_argument(
        "--avg-modules",
        type=int,
        default=AVG_MODULES_PER_COURSE,
        help=f"Assumed number of modules in an average course (default: {AVG_MODULES_PER_COURSE}).",
    )
    parser.add_argument(
        "--avg-activities-per-module",
        type=int,
        default=AVG_ACTIVITIES_PER_MODULE,
        help=f"Assumed number of activities per module (default: {AVG_ACTIVITIES_PER_MODULE}).",
    )
    parser.add_argument(
        "--output-file",
        nargs="?",
        const=DEFAULT_OUTPUT_FILENAME,
        default=None,
        metavar="PATH",
        help=(
            "Also save the report to a file, in addition to printing it. Relative paths are "
            f"resolved against the project root. Bare flag defaults to '{DEFAULT_OUTPUT_FILENAME}' "
            "there (already gitignored)."
        ),
    )
    return parser.parse_args()


def _resolve_output_path(output_file: str) -> Path:
    """Resolve an --output-file value to an absolute path, relative to the project root.

    Args:
        output_file: The raw --output-file value (a bare filename or a path).

    Returns:
        The path to write to - unchanged if already absolute, otherwise
        joined onto REPO_ROOT.
    """
    path = Path(output_file)
    return path if path.is_absolute() else REPO_ROOT / path


def _configure_settings(args: argparse.Namespace) -> str:
    """Apply the CLI args to the throwaway UserSettings row.

    Returns:
        The actual model id generation will run against, for the report header.
    """
    settings = UserSettings.get_or_create()
    if args.provider:
        settings.model_provider_tier = "hosted"
        settings.model_provider_hosted_provider = args.provider
        settings.model_provider_hosted_model = args.hosted_model
        settings.model_provider_api_key = args.api_key
        actual_model = args.hosted_model or f"({args.provider} default)"
    else:
        settings.model_provider_tier = "byom"
        settings.model_provider_byom_model = args.byom_model
        settings.model_provider_byom_endpoint = args.byom_endpoint
        actual_model = f"ollama_chat/{args.byom_model}"

    if args.tavily_key:
        settings.tavily_api_key = args.tavily_key
        settings.visual_aids_enabled = True
        settings.video_embedding_enabled = True

    db.session.commit()
    return actual_model


def _feedback_prompt_text(activity) -> str:
    return activity.to_dict().get("prompt") or ""


def _first_feedback_eligible_activity(course: Course):
    """essay/project/capstone only - a reading's checkQuestion is multiple-choice,
    checked deterministically client-side like any quiz question, not free-text
    feedback."""
    for module in course.modules:
        for activity in module.activities:
            if activity.activity_type in ("essay", "project", "capstone"):
                return activity
    return None


def _first_discussion_activity(course: Course):
    for module in course.modules:
        for activity in module.activities:
            if activity.activity_type == "discussion":
                return activity
    return None


def run(args: argparse.Namespace) -> tuple[dict, str, int]:
    """Drive the dummy course end-to-end and return its usage summary.

    Returns:
        (summary, actual_model, modules_generated) - summarize_usage()'s
        dict, the model id generation actually ran against, and how many
        modules actually had content generated in this sample (needed to
        turn per-module totals into a real per-module average).
    """
    app = create_app(test=False, in_memory_db=True)
    with app.app_context():
        db.create_all()
        actual_model = _configure_settings(args)

        step = start_course(args.topic)
        while not step.done:
            step = submit_interview_answer(step.course.id, DUMMY_ANSWER)
        course_id = step.course.id

        generate_outline(course_id)
        course = approve_outline(course_id)

        module_count = len(course.modules) if args.modules == "all" else min(int(args.modules), len(course.modules))
        for module in course.modules[:module_count]:
            generate_module_activities(module.id)

        activity = _first_feedback_eligible_activity(course)
        if activity is not None:
            generate_activity_feedback(
                _feedback_prompt_text(activity),
                DUMMY_FEEDBACK_RESPONSE,
                activity.activity_type,
                "encouraging",
                course_id=activity.module.course_id,
                module_id=activity.module_id,
            )
            db.session.commit()

        discussion_activity = _first_discussion_activity(course)
        if discussion_activity is not None:
            done = False
            turn = 0
            while not done and turn < MAX_DISCUSSION_TURNS:
                turn += 1
                result = generate_discussion_reply(discussion_activity, f"{DUMMY_FEEDBACK_RESPONSE} (turn {turn})")
                db.session.commit()
                done = result.done
                discussion_activity = db.session.get(Activity, discussion_activity.id)

        return summarize_usage(course_id), actual_model, module_count


def _sum_tokens(summary: dict, call_types: set[str]) -> tuple[int, int]:
    """Sum (prompt, completion) tokens across summary["byCallType"] rows in call_types."""
    rows = [g for g in summary["byCallType"] if g["callType"] in call_types]
    return sum(g["promptTokens"] for g in rows), sum(g["completionTokens"] for g in rows)


def _call_count(summary: dict, call_type: str) -> int:
    return sum(g["totalCalls"] for g in summary["byCallType"] if g["callType"] == call_type)


def estimate_average_course_tokens(
    summary: dict, modules_sampled: int, avg_modules: int, avg_activities_per_module: int
) -> tuple[int, int]:
    """Extrapolate (prompt, completion) tokens for an "average" course from one real sampled run.

    Course-level calls (interview, outline, context compaction) are taken
    as-is - they happen once regardless of course size. Per-module and
    per-activity calls are averaged over what was actually sampled, then
    scaled by the assumed course shape.

    Args:
        summary: usage_reporting.summarize_usage()'s dict for the sampled course.
        modules_sampled: How many modules actually had content generated in this run.
        avg_modules: Assumed number of modules in an average course.
        avg_activities_per_module: Assumed number of activities per module.

    Returns:
        (prompt_tokens, completion_tokens) estimated for the average course.
    """
    course_prompt, course_completion = _sum_tokens(summary, COURSE_LEVEL_CALL_TYPES)

    module_prompt, module_completion = _sum_tokens(summary, PER_MODULE_CALL_TYPES)
    per_module_prompt = module_prompt / modules_sampled if modules_sampled else 0
    per_module_completion = module_completion / modules_sampled if modules_sampled else 0

    activity_prompt, activity_completion = _sum_tokens(summary, PER_ACTIVITY_CALL_TYPES)
    activities_sampled = _call_count(summary, "module_activity")
    per_activity_prompt = activity_prompt / activities_sampled if activities_sampled else 0
    per_activity_completion = activity_completion / activities_sampled if activities_sampled else 0

    total_prompt = course_prompt + avg_modules * (per_module_prompt + avg_activities_per_module * per_activity_prompt)
    total_completion = course_completion + avg_modules * (
        per_module_completion + avg_activities_per_module * per_activity_completion
    )
    return round(total_prompt), round(total_completion)


def _render_report(
    summary: dict, modules_sampled: int, avg_modules: int, avg_activities_per_module: int
) -> str:
    prompt_tokens, completion_tokens = estimate_average_course_tokens(
        summary, modules_sampled, avg_modules, avg_activities_per_module
    )
    activities_sampled = _call_count(summary, "module_activity")

    lines = [
        "## Assumptions",
        "",
        f"- An average course has **{avg_modules} modules**, each with **{avg_activities_per_module} "
        "activities** (override with --avg-modules / --avg-activities-per-module).",
        "- Interview length, outline size, and per-module/per-activity token costs are measured "
        f"directly from this run's real generation ({modules_sampled} module(s), {activities_sampled} "
        "activity/activities sampled), then scaled to the assumed course shape above.",
        "- Excludes generation that isn't part of producing the course itself: activity feedback "
        "(a per-submission, on-demand cost) and document summaries (document-grounded courses only).",
        f"- Estimated average course: ~{prompt_tokens:,} prompt tokens + ~{completion_tokens:,} completion tokens.",
        "",
        "## Estimated cost of generating an average course",
        "",
        "| Reference model | $/1M input | $/1M output | Estimated cost for an average course |",
        "|---|---|---|---|",
    ]
    for name, key in REFERENCE_MODELS.items():
        rate = rate_per_million_tokens(key)
        cost = estimate_cost(prompt_tokens, completion_tokens, key)
        if rate is None or cost is None:
            lines.append(f"| {name} | - | - | - |")
            continue
        input_rate, output_rate = rate
        lines.append(f"| {name} | ${input_rate:.2f} | ${output_rate:.2f} | ${cost:.4f} |")

    return "\n".join(lines)


if __name__ == "__main__":
    parsed_args = _parse_args()
    summary_result, _actual_model, modules_generated = run(parsed_args)
    report = _render_report(
        summary_result, modules_generated, parsed_args.avg_modules, parsed_args.avg_activities_per_module
    )
    print(report)

    if parsed_args.output_file:
        output_path = _resolve_output_path(parsed_args.output_file)
        output_path.write_text(report + "\n")
        print(f"\nWrote report to {output_path}")
