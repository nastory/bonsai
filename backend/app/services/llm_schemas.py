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
    prompt: str | None = None
    # Populated when this activity's content drew on a retrieved search
    # result (see module_retrieval.py); None when it didn't (no search
    # results for this activity, or no Tavily key configured).
    citations: list[CitationSchema] | None = None


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
