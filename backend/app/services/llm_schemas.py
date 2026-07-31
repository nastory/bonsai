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

from pydantic import BaseModel, Field, ValidationError


class LLMOutputValidationError(Exception):
    """Raised when an LLM response is not valid JSON or doesn't match its expected schema."""


class InterviewStepSchema(BaseModel):
    """Expected shape of a course_interview.md response."""

    done: bool
    question: str | None = None


class CourseModuleSchema(BaseModel):
    """Expected shape of one module within a course_outline.md response."""

    title: str
    description: str
    estimatedTimeline: str
    learningOutcomes: list[str] = Field(default_factory=list)


class CourseOutlineSchema(BaseModel):
    """Expected shape of a course_outline.md response."""

    title: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)
    estimatedTimeline: str
    modules: list[CourseModuleSchema]


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
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMOutputValidationError(f"LLM response was not valid JSON: {e}") from e

    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise LLMOutputValidationError(f"LLM response didn't match the expected schema: {e}") from e
