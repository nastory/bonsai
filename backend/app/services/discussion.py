"""Real, multi-turn discussion generation for a discussion activity.

Per docs/course_content_definitions.md: discussion is a genuine back-and-forth
conversation (target 3, hard cap 5 exchanges), not the single-shot
submit-and-get-feedback flow every other free-response activity type uses
(see activity_feedback.py) - so it gets its own turn-counting/generation
service, deliberately mirroring course_generation.py's interview-flow
pattern (_advance_interview()/InterviewStepSchema/MAX_INTERVIEW_QUESTIONS)
rather than reusing generate_activity_feedback(), which has no notion of
"turn N of M" or a running per-activity history.

Turns persist as ConversationMessage rows tagged with this activity's id
(kind="discussion_reply" for every turn except the closing one, which gets
"discussion_wrapup") - see Activity.to_dict()'s discussion branch, which is
how a page refresh sees an in-progress discussion again with no separate
GET endpoint needed.
"""

from dataclasses import dataclass

from flask import current_app

from app.extensions import db
from app.models import Activity, ConversationMessage, Module, Course, UserSettings
from app.services.activity_feedback import TONE_INSTRUCTIONS
from app.services.course_context import assemble_learning_history, conversation_turns
from app.services.llm import complete
from app.services.llm_schemas import DiscussionTurnSchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt

# Per docs/course_content_definitions.md: "at most 5 chat interactions,
# target around 3."
MAX_DISCUSSION_TURNS = 5
TARGET_DISCUSSION_TURNS = 3

# Appended in code, not left to the model to remember every time - same
# "deterministic over model-authored" precedent as citations/correctAnswerIndex
# elsewhere in this codebase. The model's own closing reply still wraps up
# the actual discussion content; this just guarantees the learner is
# explicitly told the activity is finished, regardless of model compliance.
DISCUSSION_COMPLETE_NOTE = "\n\nGood job — you've completed this activity and can move on to the next."


class DiscussionNotAvailableError(Exception):
    """Raised when a discussion turn is requested for a non-discussion or already-finished activity."""


@dataclass
class DiscussionTurnResult:
    """One turn's result: Bonsai's reply, and whether the discussion is now finished."""

    done: bool
    message: str


def generate_discussion_reply(activity: Activity, reply: str) -> DiscussionTurnResult:
    """Record a learner's reply and generate Bonsai's next discussion turn.

    Args:
        activity: The discussion activity (must be activity_type="discussion").
        reply: The learner's reply text.

    Returns:
        Bonsai's next turn: whether the discussion is now done, and its message.

    Raises:
        DiscussionNotAvailableError: If the activity isn't a discussion, or
            this discussion has already finished.
        LLMOutputValidationError: If the model's response doesn't match
            DiscussionTurnSchema.
    """
    if activity.activity_type != "discussion":
        raise DiscussionNotAvailableError(f"Activity '{activity.id}' is not a discussion activity")
    if any(m.kind == "discussion_wrapup" for m in activity.conversation_messages):
        raise DiscussionNotAvailableError(f"Discussion activity '{activity.id}' has already finished")

    module = activity.module
    course = module.course
    # This reply's own turn number, counting only the learner's messages -
    # e.g. the learner's first-ever reply here is turn 1, regardless of how
    # many assistant messages exist.
    current_turn = sum(1 for m in activity.conversation_messages if m.role == "user") + 1

    db.session.add(
        ConversationMessage(
            course_id=course.id,
            module_id=module.id,
            activity_id=activity.id,
            role="user",
            kind="discussion_reply",
            content=reply,
        )
    )

    turn = _next_discussion_turn(activity, module, course, current_turn)
    # Hard cap enforced in code, not trusted to the model - same "deterministic
    # over model-authored" precedent as citations/correctAnswerIndex elsewhere.
    done = turn.done or current_turn >= MAX_DISCUSSION_TURNS
    message = turn.message + DISCUSSION_COMPLETE_NOTE if done else turn.message

    db.session.add(
        ConversationMessage(
            course_id=course.id,
            module_id=module.id,
            activity_id=activity.id,
            role="assistant",
            kind="discussion_wrapup" if done else "discussion_reply",
            content=message,
        )
    )
    return DiscussionTurnResult(done=done, message=message)


def _next_discussion_turn(activity: Activity, module: Module, course: Course, current_turn: int) -> DiscussionTurnSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        done = current_turn >= TARGET_DISCUSSION_TURNS
        return DiscussionTurnSchema(
            reflection="[MOCK] reflection",
            done=done,
            message="[MOCK] Thanks for sharing that - good discussion." if done else f"[MOCK] Discussion reply {current_turn}.",
        )

    settings = UserSettings.get_or_create()
    system_prompt = load_prompt(
        "module_discussion",
        module_title=module.title,
        topic=activity.to_dict().get("prompt") or "",
        history=assemble_learning_history(course),
        tone_instructions=TONE_INSTRUCTIONS.get(settings.feedback_tone, TONE_INSTRUCTIONS["encouraging"]),
        turns_so_far=current_turn - 1,
        target_turns=TARGET_DISCUSSION_TURNS,
        max_turns=MAX_DISCUSSION_TURNS,
    )
    messages = [{"role": "system", "content": system_prompt}] + conversation_turns(
        course, {"discussion_reply", "discussion_wrapup"}, activity_id=activity.id
    )
    raw = complete(
        messages=messages,
        schema=DiscussionTurnSchema,
        course_id=course.id,
        module_id=module.id,
        call_type="activity_discussion",
        content_type="discussion",
        label=activity.title,
        **resolve_model_config(),
    )
    return validate_llm_json(raw, DiscussionTurnSchema)
