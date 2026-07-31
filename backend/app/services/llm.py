"""Wrapper around LiteLLM completion calls.

This is the only module that imports litellm directly, so both the runtime
LLM_TEST_MODE flag and the pytest suite have a single seam to intercept.
"""

import litellm
from flask import current_app


def complete(
    messages: list[dict[str, str]],
    model: str,
    api_key: str | None = None,
    api_base: str | None = None,
) -> str:
    """Get a chat completion's text content.

    Args:
        messages: Chat messages in the standard role/content shape.
        model: The LiteLLM-recognized model identifier to call (e.g.
            "claude-3-5-sonnet-20241022" for a hosted model, or
            "ollama/llama3" for a local one).
        api_key: The provider API key, for hosted models. Omitted entirely
            (not passed as None) when not given, so BYOM calls that need
            no key don't send a meaningless one.
        api_base: The provider's base URL, for BYOM/local models.

    Returns:
        The completion's text content. Returns a canned response instead
        of calling a real provider when ``LLM_TEST_MODE`` is set.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_completion(messages)

    kwargs: dict = {"model": model, "messages": messages}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = litellm.completion(**kwargs)
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
