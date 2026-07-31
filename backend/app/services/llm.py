"""Wrapper around LiteLLM completion calls.

This is the only module that imports litellm directly, so both the runtime
LLM_TEST_MODE flag and the pytest suite have a single seam to intercept.
"""

import litellm
from flask import current_app


def complete(messages: list[dict[str, str]], model: str) -> str:
    """Get a chat completion's text content.

    Args:
        messages: Chat messages in the standard role/content shape.
        model: The LiteLLM-recognized model identifier to call.

    Returns:
        The completion's text content. Returns a canned response instead
        of calling a real provider when ``LLM_TEST_MODE`` is set.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_completion(messages)

    response = litellm.completion(model=model, messages=messages)
    return response.choices[0].message.content


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
