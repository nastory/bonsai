"""Tests for the search/fetch/evaluate tool-calling loop.

Runs with LLM_TEST_MODE off (real_llm_app fixture) so the real
complete_with_tools()/litellm.completion path is exercised, but
litellm.completion and the retrieval functions themselves are monkeypatched,
so no network call happens at all.
"""

import json

from app.services.retrieval_agent import MAX_TOOL_ITERATIONS, run_agent


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: dict) -> None:
        self.id = call_id
        self.function = _FakeFunction(name, json.dumps(arguments))


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeMessage:
    def __init__(self, content: str | None, tool_calls: list | None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, message: _FakeMessage) -> None:
        self.choices = [_FakeChoice(message)]


def test_run_agent_returns_content_when_model_calls_no_tools(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.litellm.completion",
        lambda **kwargs: _FakeResponse(_FakeMessage("final activities JSON", None)),
    )

    with real_llm_app.app_context():
        result = run_agent(
            messages=[{"role": "user", "content": "Generate the module"}],
            model_config={"model": "claude-3-5-sonnet-20241022"},
            tavily_api_key="tvly-test",
        )

    assert result == "final activities JSON"


def test_run_agent_executes_web_search_tool_call_and_continues(real_llm_app, monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_completion(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            tool_call = _FakeToolCall("call-1", "web_search", {"query": "GPUs"})
            return _FakeResponse(_FakeMessage(None, [tool_call]))
        # Second call: the tool result should already be in the conversation.
        assert any(m.get("role") == "tool" for m in kwargs["messages"])
        return _FakeResponse(_FakeMessage("final activities JSON", None))

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
    monkeypatch.setattr(
        "app.services.retrieval_agent.web_search",
        lambda query, api_key, max_results=5: [{"title": "T", "url": "https://example.com", "content": "c"}],
    )

    with real_llm_app.app_context():
        result = run_agent(
            messages=[{"role": "user", "content": "Generate the module"}],
            model_config={"model": "claude-3-5-sonnet-20241022"},
            tavily_api_key="tvly-test",
        )

    assert result == "final activities JSON"
    assert call_count["n"] == 2


def test_run_agent_executes_fetch_page_tool_call(real_llm_app, monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_completion(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            tool_call = _FakeToolCall("call-1", "fetch_page", {"url": "https://example.com/gpu"})
            return _FakeResponse(_FakeMessage(None, [tool_call]))
        return _FakeResponse(_FakeMessage("final activities JSON", None))

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
    fetch_calls = []
    monkeypatch.setattr(
        "app.services.retrieval_agent.fetch_page",
        lambda url, api_key: fetch_calls.append(url) or {"url": url, "content": "full text"},
    )

    with real_llm_app.app_context():
        result = run_agent(
            messages=[{"role": "user", "content": "Generate the module"}],
            model_config={"model": "claude-3-5-sonnet-20241022"},
            tavily_api_key="tvly-test",
        )

    assert result == "final activities JSON"
    assert fetch_calls == ["https://example.com/gpu"]


def test_run_agent_forces_a_final_answer_after_max_iterations(real_llm_app, monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_completion(**kwargs):
        call_count["n"] += 1
        if "tools" in kwargs:
            # Always calls a tool, never stops on its own.
            tool_call = _FakeToolCall(f"call-{call_count['n']}", "web_search", {"query": "GPUs"})
            return _FakeResponse(_FakeMessage(None, [tool_call]))
        # The final, tool-less nudge call goes through complete(), not complete_with_tools.
        return _FakeResponse(_FakeMessage("forced final answer", None))

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
    monkeypatch.setattr(
        "app.services.retrieval_agent.web_search",
        lambda query, api_key, max_results=5: [{"title": "T", "url": "https://example.com", "content": "c"}],
    )

    with real_llm_app.app_context():
        result = run_agent(
            messages=[{"role": "user", "content": "Generate the module"}],
            model_config={"model": "claude-3-5-sonnet-20241022"},
            tavily_api_key="tvly-test",
        )

    assert result == "forced final answer"
    assert call_count["n"] == MAX_TOOL_ITERATIONS + 1
