"""Tests for the LiteLLM wrapper service.

These pin down the one seam the rest of the app depends on: in test mode,
no real provider is ever called; outside test mode, litellm.completion is
called and its response is unwrapped to plain text.
"""

from flask import Flask
from pydantic import BaseModel

from app.extensions import db as _db
from app.models import LLMUsageLog
from app.services.llm import OLLAMA_NUM_CTX, complete, complete_with_tools


class _DummySchema(BaseModel):
    value: str


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens


class _FakeResponse:
    def __init__(self, content: str, usage: _FakeUsage | None = None) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = usage


def test_complete_returns_canned_response_in_test_mode(app: Flask) -> None:
    with app.app_context():
        result = complete(
            messages=[{"role": "user", "content": "Tell me about GPUs"}],
            model="claude-3-5-sonnet-20241022",
            schema=_DummySchema,
        )

    assert isinstance(result, str)
    assert "Tell me about GPUs" in result


def test_complete_does_not_call_litellm_in_test_mode(app: Flask, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("litellm.completion should not be called in test mode")

    monkeypatch.setattr("app.services.llm.litellm.completion", fail_if_called)

    with app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema)


def test_complete_calls_litellm_when_not_in_test_mode(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(model, messages, **kwargs):
        captured["model"] = model
        captured["messages"] = messages
        return _FakeResponse("a real response")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        result = complete(
            messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema
        )

    assert result == "a real response"
    assert captured["model"] == "claude-3-5-sonnet-20241022"
    assert captured["messages"] == [{"role": "user", "content": "Hi"}]


def test_complete_forwards_api_key_and_api_base_when_given(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(
            messages=[{"role": "user", "content": "Hi"}],
            model="ollama_chat/llama3",
            schema=_DummySchema,
            api_key="sk-test",
            api_base="http://localhost:11434",
        )

    assert captured["model"] == "ollama_chat/llama3"
    assert captured["api_key"] == "sk-test"
    assert captured["api_base"] == "http://localhost:11434"


def test_complete_requests_schema_constrained_json_for_hosted_models(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema)

    assert captured["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "_DummySchema", "schema": _DummySchema.model_json_schema()},
    }
    assert "format" not in captured


def test_complete_requests_schema_constrained_json_for_ollama_models(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="ollama_chat/llama3", schema=_DummySchema)

    assert captured["format"] == _DummySchema.model_json_schema()
    assert "response_format" not in captured


def test_complete_sets_a_larger_num_ctx_for_ollama_models(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="ollama_chat/llama3", schema=_DummySchema)

    assert captured["num_ctx"] == OLLAMA_NUM_CTX


def test_complete_does_not_set_num_ctx_for_hosted_models(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema)

    assert "num_ctx" not in captured


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeMessageWithTools:
    def __init__(self, content: str | None, tool_calls: list | None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoiceWithTools:
    def __init__(self, message: _FakeMessageWithTools) -> None:
        self.message = message


class _FakeResponseWithTools:
    def __init__(self, message: _FakeMessageWithTools) -> None:
        self.choices = [_FakeChoiceWithTools(message)]


def test_complete_with_tools_returns_the_raw_message(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    fake_message = _FakeMessageWithTools("a final answer", None)
    monkeypatch.setattr(
        "app.services.llm.litellm.completion", lambda **kwargs: _FakeResponseWithTools(fake_message)
    )

    with real_app.app_context():
        result = complete_with_tools(
            messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", tools=[]
        )

    assert result is fake_message
    assert result.content == "a final answer"
    assert result.tool_calls is None


def test_complete_with_tools_forwards_tools_and_model_config(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}
    tool_calls = [_FakeToolCall("call-1", "web_search", '{"query": "GPUs"}')]

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponseWithTools(_FakeMessageWithTools(None, tool_calls))

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    tools = [{"type": "function", "function": {"name": "web_search"}}]
    with real_app.app_context():
        result = complete_with_tools(
            messages=[{"role": "user", "content": "Hi"}],
            model="ollama_chat/llama3",
            tools=tools,
            api_key="sk-test",
            api_base="http://localhost:11434",
        )

    assert captured["model"] == "ollama_chat/llama3"
    assert captured["tools"] == tools
    assert captured["api_key"] == "sk-test"
    assert captured["api_base"] == "http://localhost:11434"
    assert result.tool_calls == tool_calls


def test_complete_omits_api_key_and_api_base_when_not_given(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse("ok")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema)

    assert "api_key" not in captured
    assert "api_base" not in captured


def test_complete_logs_usage_when_call_type_is_given(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("ok", _FakeUsage(100, 20))
    )

    with real_llm_app.app_context():
        complete(
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-3-5-sonnet-20241022",
            schema=_DummySchema,
            course_id="c1",
            module_id="m1",
            call_type="module_activity",
            content_type="reading",
            label="Intro to X",
        )
        _db.session.commit()

        rows = _db.session.execute(_db.select(LLMUsageLog)).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.course_id == "c1"
    assert row.module_id == "m1"
    assert row.call_type == "module_activity"
    assert row.content_type == "reading"
    assert row.label == "Intro to X"
    assert row.model == "claude-3-5-sonnet-20241022"
    assert row.prompt_tokens == 100
    assert row.completion_tokens == 20
    assert row.total_tokens == 120


def test_complete_does_not_log_usage_without_call_type(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("ok", _FakeUsage(100, 20))
    )

    with real_llm_app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022", schema=_DummySchema)
        _db.session.commit()

        rows = _db.session.execute(_db.select(LLMUsageLog)).scalars().all()

    assert rows == []


def test_complete_does_not_log_usage_when_response_has_no_usage(real_llm_app, monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: _FakeResponse("ok"))

    with real_llm_app.app_context():
        complete(
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-3-5-sonnet-20241022",
            schema=_DummySchema,
            call_type="course_outline",
        )
        _db.session.commit()

        rows = _db.session.execute(_db.select(LLMUsageLog)).scalars().all()

    assert rows == []


def test_complete_logs_estimated_usage_in_test_mode_when_call_type_is_given(app: Flask, db) -> None:
    with app.app_context():
        complete(
            messages=[{"role": "user", "content": "Tell me about GPUs"}],
            model="ollama_chat/llama3",
            schema=_DummySchema,
            course_id="c1",
            call_type="course_outline",
        )
        db.session.commit()

        rows = db.session.execute(db.select(LLMUsageLog)).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert row.course_id == "c1"
    assert row.call_type == "course_outline"
    assert row.model == "ollama_chat/llama3"
    assert row.prompt_tokens > 0
    assert row.completion_tokens > 0
    assert row.total_tokens == row.prompt_tokens + row.completion_tokens


def test_complete_does_not_log_in_test_mode_without_call_type(app: Flask, db) -> None:
    with app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="ollama_chat/llama3", schema=_DummySchema)
        db.session.commit()

        rows = db.session.execute(db.select(LLMUsageLog)).scalars().all()

    assert rows == []
