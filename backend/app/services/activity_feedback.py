"""Real, on-demand feedback for a learner's free-text activity response.

Per the PRD: exercises are feedback-only, never graded. Quizzes/assessments
already get this from a real generated explanation (see
GeneratedActivitySchema's correctAnswerIndex/explanation). This module covers
the other free-response cases - essay/project/discussion activities, and a
reading's optional comprehension check (GeneratedActivitySchema.checkPrompt) -
which used to show fixed canned copy regardless of what the learner actually
wrote (see the now-deleted lib/feedback.ts on the frontend). Generated fresh
per submission instead, grounded in both the activity's own prompt and the
learner's real response, and in the learner's configured feedback tone
(UserSettings.feedback_tone) - the one place that setting actually reaches
generated content, rather than picking between two hardcoded frontend strings.
"""

from flask import current_app

from app.services.llm import complete
from app.services.llm_schemas import ActivityFeedbackSchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt

TONE_INSTRUCTIONS = {
    "encouraging": "Warm and encouraging. Affirm what's working before gently pointing at what could go deeper.",
    "straightforward": "Direct and concise. Skip the encouragement - focus on the substance and what's missing or could be sharpened.",
}


def generate_activity_feedback(
    prompt_text: str,
    response_text: str,
    kind: str,
    tone: str,
    course_id: str | None = None,
    module_id: str | None = None,
) -> str:
    """Generate real feedback on a learner's free-text response.

    Args:
        prompt_text: The activity's own seed prompt/question (its `prompt`
            for essay/project/discussion, or `checkPrompt` for a reading's
            comprehension check).
        response_text: What the learner actually wrote.
        kind: One of "essay", "project", "discussion", "check" - shapes the
            prompt's framing of what kind of response this is.
        tone: UserSettings.feedback_tone ("encouraging" or "straightforward").
        course_id: The activity's course, for usage logging (see llm.py's
            complete()). None skips logging.
        module_id: The activity's module, for usage logging.

    Returns:
        A short feedback message referencing the learner's actual response.

    Raises:
        LLMOutputValidationError: If the model's response doesn't match
            ActivityFeedbackSchema.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return f"[MOCK] Feedback on your {kind} response."

    messages = [
        {
            "role": "system",
            "content": load_prompt(
                "activity_feedback",
                kind=kind,
                tone_instructions=TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["encouraging"]),
            ),
        },
        {"role": "user", "content": _feedback_data_message(prompt_text, response_text)},
    ]
    raw = complete(
        messages=messages,
        schema=ActivityFeedbackSchema,
        course_id=course_id,
        module_id=module_id,
        call_type="activity_feedback",
        content_type=kind,
        **resolve_model_config(),
    )
    parsed = validate_llm_json(raw, ActivityFeedbackSchema)
    return parsed.feedback


def _feedback_data_message(prompt_text: str, response_text: str) -> str:
    return f"Activity prompt: {prompt_text}\n\nLearner's response: {response_text}"
