"""Wrapper around LiteLLM completion calls.

This is the only module that imports litellm directly, so both the runtime
LLM_TEST_MODE flag and the pytest suite have a single seam to intercept.
"""

import litellm
from flask import current_app
from pydantic import BaseModel

from app.extensions import db
from app.models import LLMUsageLog

# Ollama's own default is ~2048 tokens - too small for this app's real
# prompts (accumulated activity history within a module, retrieved document
# chunks, course learning history) and already confirmed live to cause
# truncated/malformed responses under real usage (see docs/todo.md and
# module_generation.py's module docstring). 4x the default, picked with
# real VRAM tradeoffs in mind (a bigger num_ctx costs Ollama proportionally
# more memory) rather than maximized blindly - verified live against a real
# Ollama instance, not just asserted from documentation.
OLLAMA_NUM_CTX = 8192


def complete(
    messages: list[dict[str, str]],
    model: str,
    schema: type[BaseModel] | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    *,
    course_id: str | None = None,
    module_id: str | None = None,
    call_type: str | None = None,
    content_type: str | None = None,
    label: str | None = None,
) -> str:
    """Get a chat completion's text content, optionally constrained to match a schema.

    Args:
        messages: Chat messages in the standard role/content shape.
        model: The LiteLLM-recognized model identifier to call (e.g.
            "claude-3-5-sonnet-20241022" for a hosted model, or
            "ollama_chat/llama3" for a local one).
        schema: The Pydantic schema the response must match, when the caller
            is going to feed the result into validate_llm_json() against
            this same schema (true of every call site except
            retrieval_agent.py's final free-text nudge, which wants plain
            text, not JSON). Without a real schema constraint, weaker/local
            models occasionally answer conversationally instead of with
            JSON at all (confirmed against real Ollama/llama3), or with
            syntactically valid JSON in the wrong shape (also confirmed).
            "Valid JSON, any shape" alone (a plain ``{"type": "json_object"}``
            mode) doesn't catch the second failure; a real schema does.
        api_key: The provider API key, for hosted models. Omitted entirely
            (not passed as None) when not given, so BYOM calls that need
            no key don't send a meaningless one.
        api_base: The provider's base URL, for BYOM/local models.
        course_id: The course this call is generating for, if any. Together
            with call_type, opts this call into usage logging (see
            _log_usage()) - omitted entirely, this call is simply not logged.
        module_id: The module this call is generating for, if any. None for
            course-level calls (interview, outline, ...).
        call_type: Which generation step this is (e.g. "course_outline",
            "module_activity", "activity_feedback") - required for usage
            logging to happen at all.
        content_type: For call_type="module_activity"/"activity_feedback"
            rows, which kind of content (reading/quiz/essay/...), so a usage
            report can group by it.
        label: Free-text context for this call (e.g. an activity's planned
            title), for drilling into one specific lesson's generation.

    Returns:
        The completion's text content. Returns a canned response instead
        of calling a real provider when ``LLM_TEST_MODE`` is set.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        content = _mock_completion(messages)
        if call_type is not None:
            prompt_tokens = sum(_rough_token_count(m.get("content", "")) for m in messages)
            _log_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=_rough_token_count(content),
                course_id=course_id,
                module_id=module_id,
                call_type=call_type,
                content_type=content_type,
                label=label,
            )
        return content

    kwargs: dict = {"model": model, "messages": messages}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    if model.startswith("ollama"):
        kwargs["num_ctx"] = OLLAMA_NUM_CTX

    if schema is not None:
        json_schema = schema.model_json_schema()
        if model.startswith("ollama"):
            # Ollama's own schema-constrained decoding: a JSON schema passed
            # as the native "format" field (requires Ollama >=0.5 — see
            # README). Not routed through response_format: LiteLLM's Ollama
            # translation only forwards response_format's plain
            # {"type": "json_object"} case (unconstrained "valid JSON, any
            # shape"), not a real json_schema.
            kwargs["format"] = json_schema
        else:
            # OpenAI: native Structured Outputs. Anthropic: LiteLLM
            # translates this same shape into a forced tool-call constrained
            # to the schema, transparently unwrapping it back into a normal
            # JSON string content (see litellm/llms/anthropic/chat/transformation.py's
            # json_mode handling) so this call site doesn't need to know the
            # difference. Deliberately not requesting OpenAI's "strict": true:
            # several of this codebase's schemas have optional fields, which
            # strict mode's stricter shape rules (every field required, no
            # plain-optional) aren't guaranteed to satisfy — unverified
            # without a live OpenAI key in this environment, so left off
            # rather than risk breaking hosted generation silently.
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema},
            }

    response = litellm.completion(**kwargs)
    # getattr, not response.usage: several tests stand in a hand-rolled fake
    # response (only .choices[0].message.content) for litellm.completion, so
    # a real response missing usage - or a fake one that doesn't model it at
    # all - just means this call isn't logged, not a crash.
    usage = getattr(response, "usage", None)
    if call_type is not None and usage is not None:
        _log_usage(
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            course_id=course_id,
            module_id=module_id,
            call_type=call_type,
            content_type=content_type,
            label=label,
        )
    return response.choices[0].message.content


def complete_with_tools(
    messages: list[dict],
    model: str,
    tools: list[dict],
    api_key: str | None = None,
    api_base: str | None = None,
):
    """Get a chat completion with tool-calling enabled, returning the raw message.

    Unlike complete(), this always makes a real call: it's only ever invoked
    from a code path (the retrieval agent) that's already skipped entirely
    in LLM_TEST_MODE, matching this codebase's existing convention of mocking
    at the generation-function level rather than inside the LLM wrapper.

    Args:
        messages: Chat messages in the standard role/content shape.
        model: The LiteLLM-recognized model identifier to call.
        tools: OpenAI-style tool/function schemas the model may call.
        api_key: The provider API key, for hosted models.
        api_base: The provider's base URL, for BYOM/local models.

    Returns:
        The raw response message, exposing `.content` and `.tool_calls`
        (the latter is None/empty when the model didn't call a tool).
    """
    kwargs: dict = {"model": model, "messages": messages, "tools": tools}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = litellm.completion(**kwargs)
    return response.choices[0].message


def _rough_token_count(text: str) -> int:
    """Approximate a token count from raw text, for LLM_TEST_MODE logging only.

    Real (non-test-mode) calls always use litellm's actual reported usage -
    this ~4-chars-per-token rule of thumb only exists so the usage-logging
    code path is exercised deterministically under tests, without needing a
    real tokenizer dependency.

    Args:
        text: The text to estimate a token count for.

    Returns:
        An approximate token count, at least 1.
    """
    return max(1, len(text) // 4)


def _log_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    course_id: str | None,
    module_id: str | None,
    call_type: str,
    content_type: str | None,
    label: str | None,
) -> None:
    """Record one completion call's token usage, best-effort.

    Adds the row to the current session without committing - it rides along
    with whichever commit the calling request handler already does (see
    complete()'s docstring). A logging failure must never break real
    generation, so any exception here is swallowed after a warning.

    Args:
        model: The exact model id passed to litellm.completion().
        prompt_tokens: Tokens consumed by the prompt.
        completion_tokens: Tokens consumed by the completion.
        course_id: The course this call generated for, if any.
        module_id: The module this call generated for, if any.
        call_type: Which generation step this is.
        content_type: The content type (reading/quiz/...), if relevant.
        label: Free-text context for this call, if any.
    """
    try:
        db.session.add(
            LLMUsageLog(
                course_id=course_id,
                module_id=module_id,
                call_type=call_type,
                content_type=content_type,
                label=label,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        )
    except Exception:
        current_app.logger.warning("Failed to log LLM usage for call_type=%s", call_type, exc_info=True)


def _mock_completion(messages: list[dict[str, str]]) -> str:
    """Build a deterministic canned response standing in for a real completion.

    Args:
        messages: Chat messages in the standard role/content shape.

    Returns:
        A fixed placeholder string that echoes the last user message, so
        it's obvious in the UI when a response is mocked and what prompted it.
    """
    last_user_message = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    return f"[MOCK RESPONSE] {last_user_message}"
