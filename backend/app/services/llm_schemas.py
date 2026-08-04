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
    """Expected shape of a course_interview.md response."""

    done: bool
    question: str | None = None

    @model_validator(mode="after")
    def _question_required_when_not_done(self) -> "InterviewStepSchema":
        """Reject a response that's structurally valid but practically useless.

        `{"done": false, "question": ""}` (or `null`) passes the plain field
        types above, but leaves the learner staring at a chat with nothing to
        answer — the interview silently stalls instead of failing clearly.
        Confirmed happening against real Ollama/llama3. Raising here turns it
        into the same clear 502 every other malformed response already gets,
        instead of a confusing dead end.
        """
        if not self.done and not (self.question and self.question.strip()):
            raise ValueError('"question" must be a non-empty string when "done" is false')
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
    """

    activities: list[ActivitySearchPlanSchema]


class CitationSchema(BaseModel):
    """A citation linking generated content back to a real web source."""

    label: str
    url: str

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
