"""Schemas validating structured LLM output.

Every prompt that asks the model to "respond with JSON in this shape" has
a matching schema here. A prompt change (or an off-spec model response)
that breaks the expected shape surfaces as a clear LLMOutputValidationError
right where the response is parsed, not as a confusing KeyError or
AttributeError deep in course_generation.py.

Field names deliberately use the prompts' own camelCase (estimatedTimeline,
learningOutcomes) rather than PEP 8 snake_case: these classes exist purely
to mirror the external JSON contract, not as general Python domain models.
"""

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class LLMOutputValidationError(Exception):
    """Raised when an LLM response is not valid JSON or doesn't match its expected schema."""


class InterviewStepSchema(BaseModel):
    """Expected shape of a course_interview.md / module_direction_interview.md response.

    `coverage` comes first deliberately and is discarded by the caller: it's
    a scratchpad the model must fill in ("what's already been asked/answered,
    what's still missing") before it commits to `done`/`question`. Field
    order in a Pydantic model carries through to the JSON schema's property
    order, which schema-constrained decoding generates in order — so this
    forces the model to write out its own state-tracking before deciding,
    the same "think before answering" effect as chain-of-thought prompting,
    just inside the structured response instead of free text. Added after
    live testing showed a small local model (llama3 via Ollama) losing track
    of topics already answered a few turns back and re-asking them in
    different words, even with an explicit "don't repeat topics" instruction
    and no scratchpad — plain instruction-following wasn't enough on its own.

    `question` is always a required, non-nullable string — even when `done`
    is true, where the caller ignores its content — deliberately, not just
    when a follow-up question is expected. Making it Optional (as it used to
    be, required only via a model_validator when `done` was false) left a
    gap: schema-constrained decoding only enforces plain Pydantic-required
    fields, not a conditional requirement enforced by a validator. Ollama/
    llama3 exploited exactly that gap in practice, confirmed live, returning
    `{"done": false, "question": null}` — structurally valid against the
    Optional field, useless to the learner. Making the field itself required
    closes the gap at the decoding level (the same fix pattern as
    GeneratedQuizActivityDecodingSchema), not just at post-hoc validation.
    """

    coverage: str = Field(min_length=1)
    done: bool
    question: str = Field(min_length=1)

    @model_validator(mode="after")
    def _fields_not_blank(self) -> "InterviewStepSchema":
        """Reject whitespace-only text, which `min_length` alone wouldn't catch."""
        if not self.coverage.strip():
            raise ValueError('"coverage" must not be blank')
        if not self.question.strip():
            raise ValueError('"question" must not be blank')
        return self


class PlannedActivitySchema(BaseModel):
    """Expected shape of one planned activity within a course_outline.md module.

    Decided at outline time, alongside the rest of the syllabus: type and
    title, plus a one-to-two sentence plan of what it should cover. No
    content yet — that's module-generation's job, once this module is
    reached.
    """

    type: Literal["reading", "quiz", "essay", "project", "discussion", "assessment"]
    title: str
    plan: str


class CourseModuleSchema(BaseModel):
    """Expected shape of one module within a course_outline.md response."""

    title: str
    description: str
    estimatedTimeline: str
    learningOutcomes: list[str] = Field(default_factory=list)
    plannedActivities: list[PlannedActivitySchema] = Field(default_factory=list)


class CourseOutlineSchema(BaseModel):
    """Expected shape of a course_outline.md response."""

    title: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)
    estimatedTimeline: str
    modules: list[CourseModuleSchema]


class CourseDirectionChangeSchema(BaseModel):
    """Expected shape of a module_direction_outline.md response.

    Unlike CourseOutlineSchema, this only proposes modules — a mid-course
    "change direction" replaces what's ahead in an already-active course
    (see course_generation.py's approve_direction_change()), not the
    course's own title/description/prerequisites, which stay as they are.
    """

    modules: list[CourseModuleSchema]


class CourseContextSchema(BaseModel):
    """Expected shape of a course_context_compaction.md response.

    Condensed once, at outline approval (see course_generation.py's
    approve_outline()), from the full interview conversation and approved
    outline. Stored on Course.context_summary and read back via
    app/services/course_context.py, rather than either being reparsed as
    prose or requiring every future generation call to replay the full
    conversation.
    """

    summary: str
    learnerProfile: str
    keyDecisions: list[str] = Field(default_factory=list)


class ActivitySearchPlanSchema(BaseModel):
    """Search terms planned for one activity within a module_search_terms.md response."""

    activityIndex: int
    terms: list[str] = Field(default_factory=list)


class ModuleSearchPlanSchema(BaseModel):
    """Expected shape of a module_search_terms.md response.

    One entry per activity in the module's activity_plan, keyed by index
    (matched positionally rather than by title, which is fragile) — see
    app/services/module_retrieval.py's plan_activity_searches(), which
    validates the returned index set exactly covers the planned activities
    before this is trusted.

    videoSearchQuery/videoPosition piggyback a best-effort, once-per-module
    video-embedding suggestion onto this same call (see module_generation.py's
    _maybe_build_video_spec()) rather than a dedicated LLM call. Both are
    unconditionally required plain fields with sentinel values, not an
    Optional pair guarded by a validator — schema-constrained decoding has
    already been shown (see InterviewStepSchema's history) to not enforce a
    validator's conditional-requirement logic, only a field's own required-ness.
    """

    activities: list[ActivitySearchPlanSchema]
    # Empty string means "no good video fits this module" — most modules
    # shouldn't get one, this isn't a forced slot.
    videoSearchQuery: str
    # 0-based index in the module's *final* activity list (after any video
    # insertion) where the video belongs. Ignored when videoSearchQuery is
    # empty. Clamped defensively by the caller, never trusted raw.
    videoPosition: int


class CitationSchema(BaseModel):
    """A citation linking generated content back to its source.

    `url` is None for a document source material citation (e.g.
    "syllabus.pdf, p. 4", attached deterministically by module_generation.py
    from the actual chunk retrieved, not model-authored - see
    _generate_activities_content()'s vector-index branch) - only a web
    citation has a real URL. `label` carries the full citation text either
    way, so no separate "page" field is needed on this schema.
    """

    label: str
    url: str | None = None


class GeneratedActivitySchema(BaseModel):
    """Expected shape of one module_activity_generation.md response.

    Module generation calls this once per planned activity (see
    module_generation.py), so this is the top-level response shape for that
    call, not wrapped in a list.
    """

    type: Literal["reading", "quiz", "essay", "project", "discussion", "assessment"]
    title: str
    estimatedMinutes: int
    body: str | None = None
    question: str | None = None
    options: list[str] | None = None
    # Quiz/assessment-only: which of "options" is correct (by position, not
    # by repeating its text — see GeneratedQuizActivityDecodingSchema's
    # docstring for why an index instead of a string), and why. Required for
    # those two types (see the validator below) so the learner can actually
    # be told whether they got it right, not just given a generic "noted"
    # message — feedback-only per the PRD still means real feedback, not
    # scoring.
    correctAnswerIndex: int | None = None
    explanation: str | None = None
    prompt: str | None = None
    # Populated when this activity's content drew on a retrieved search
    # result (see module_retrieval.py); None when it didn't (no search
    # results for this activity, or no Tavily key configured).
    citations: list[CitationSchema] | None = None

    @model_validator(mode="after")
    def _quiz_and_assessment_require_a_checkable_answer(self) -> "GeneratedActivitySchema":
        """Reject a quiz/assessment with no way to tell the learner if they got it right.

        `correctAnswerIndex` must be a valid index into `options` — a
        missing or out-of-range index means the frontend has no correct
        option to check against, and `explanation` covers the "why," not
        just the "what."
        """
        if self.type in ("quiz", "assessment"):
            if self.correctAnswerIndex is None:
                raise ValueError('"correctAnswerIndex" is required for type=quiz/assessment')
            if not self.options or not (0 <= self.correctAnswerIndex < len(self.options)):
                raise ValueError('"correctAnswerIndex" must be a valid index into "options"')
            if not (self.explanation and self.explanation.strip()):
                raise ValueError('"explanation" is required for type=quiz/assessment')
        return self


class GeneratedQuizActivityDecodingSchema(BaseModel):
    """Decoding-only shape for a quiz/assessment generation call — NOT a parsing target.

    llm.py's complete() uses a schema's model_json_schema() to constrain the
    model's raw decoding (Ollama's native structured output, OpenAI's
    Structured Outputs, Anthropic's forced-tool-call translation — see
    complete()'s docstring). GeneratedActivitySchema can't be that schema for
    a quiz/assessment call: correctAnswerIndex/explanation are Optional
    there (they don't apply to every activity type sharing that one class),
    so the exported JSON schema doesn't mark them "required" — confirmed
    against real Ollama/llama3 that a model left free to omit an optional
    field often does, especially the last one or two: explanation was
    silently dropped in 2 of 3 trials, only caught after the fact by
    GeneratedActivitySchema's validator turning it into a request failure
    instead of a generation that just didn't have the gap to begin with.

    Also why this asks for an *index* into options rather than repeating the
    correct option's text: a plain JSON Schema string field has no way to
    express "must equal one of these other array values" (that's a
    cross-field constraint, which JSON Schema can't encode), so even with
    correctAnswer marked required, nothing stops the model from paraphrasing
    or lightly rewording the option instead of copying it verbatim —
    confirmed against real Ollama/llama3: required alone dropped the
    explanation-missing failures to 0/6, but a text correctAnswer still
    failed to exactly match any option in 3 of those 6. An index is a small
    integer already validated in-range by the schema's own type/bounds
    (see the validator on GeneratedActivitySchema), so there's no string to
    get slightly wrong.

    module_generation.py's _generate_activities_content() passes this
    instead, only for schema=, only when the planned activity's type is
    quiz/assessment — the response returned is still parsed and validated
    against GeneratedActivitySchema as normal, since that's what needs to
    handle every activity type's actual shape (title/estimatedMinutes/type
    duplicated here only so a real JSON schema can be exported; not meant
    to be instantiated).
    """

    type: Literal["quiz", "assessment"]
    title: str
    estimatedMinutes: int
    question: str
    options: list[str]
    correctAnswerIndex: int
    explanation: str


class ModuleDigestSchema(BaseModel):
    """Expected shape of a module_digest.md response.

    Generated once, right after a module's activities finish generating
    (see module_generation.py), and persisted as a "module_learning_digest"
    ConversationMessage. This is the condensed memory later modules build on
    via app/services/course_context.py's assemble_learning_history() —
    deliberately not the full activity text.
    """

    digest: str


class DocumentSummarySchema(BaseModel):
    """Expected shape of a document_summary.md response.

    Generated once per attached document, at ingestion time (see
    course_generation.py's _ingest_source_materials()), and persisted onto
    SourceMaterial.interview_summary — the interview prompt uses this
    instead of the document's full extracted text, which stays reserved for
    outline/module generation.
    """

    summary: str


class VisualAidSchema(BaseModel):
    """One suggested image placement within a reading activity's body."""

    query: str
    caption: str
    anchorText: str


class VisualAidPlanSchema(BaseModel):
    """Expected shape of a lesson_visual_aids.md response.

    Generated once per reading activity, after its body is written (see
    module_generation.py), only when UserSettings.visual_aids_enabled and a
    Tavily key are both set. 0-3 aids per the prompt's own instruction -
    not enforced here since fewer (including zero) is always valid; more
    than a handful would just mean the model didn't follow instructions,
    which the splicing step degrades gracefully against anyway (an aid
    whose anchorText isn't found verbatim in the body is silently skipped).
    """

    aids: list[VisualAidSchema] = Field(default_factory=list)


class VideoSelectionSchema(BaseModel):
    """Expected shape of a module_video_selection.md response.

    Generated once per module, only when a video search actually turned up
    candidates worth choosing among (see module_generation.py's
    _select_video()) - the model picks which of a few real Tavily results is
    the best fit and writes a caption, rather than being trusted to author a
    video url/id itself. Both fields are unconditionally required plain
    values, not an Optional pair - `selectedIndex: -1` is the "none of these
    are a good fit" sentinel, same reasoning as ModuleSearchPlanSchema's
    videoSearchQuery/videoPosition above.
    """

    selectedIndex: int
    caption: str


def validate_llm_json(raw: str, schema: type[BaseModel]) -> BaseModel:
    """Parse and validate an LLM response against an expected schema.

    Args:
        raw: The model's raw text response, possibly wrapped in a markdown
            code fence despite being asked for JSON only.
        schema: The Pydantic model describing the expected shape.

    Returns:
        A validated instance of ``schema``.

    Raises:
        LLMOutputValidationError: If the response isn't valid JSON, or
            doesn't match the schema.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        # strict=False: models frequently emit literal newlines inside long
        # free-text fields (e.g. an activity's "body") instead of escaping
        # them as \n, which the JSON spec technically disallows in strings.
        # Real models do this often enough (confirmed against Ollama/llama3)
        # that failing on it isn't a useful signal of actually malformed output.
        data = json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        raise LLMOutputValidationError(f"LLM response was not valid JSON: {e}") from e

    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise LLMOutputValidationError(f"LLM response didn't match the expected schema: {e}") from e
