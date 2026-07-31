"""Tests for the LiteLLM wrapper service.

These pin down the one seam the rest of the app depends on: in test mode,
no real provider is ever called; outside test mode, litellm.completion is
called and its response is unwrapped to plain text.
"""

from flask import Flask

from app.services.llm import complete


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_complete_returns_canned_response_in_test_mode(app: Flask) -> None:
    with app.app_context():
        result = complete(
            messages=[{"role": "user", "content": "Tell me about GPUs"}],
            model="claude-3-5-sonnet-20241022",
        )

    assert isinstance(result, str)
    assert "Tell me about GPUs" in result


def test_complete_does_not_call_litellm_in_test_mode(app: Flask, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("litellm.completion should not be called in test mode")

    monkeypatch.setattr("app.services.llm.litellm.completion", fail_if_called)

    with app.app_context():
        complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022")


def test_complete_calls_litellm_when_not_in_test_mode(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_completion(model, messages):
        captured["model"] = model
        captured["messages"] = messages
        return _FakeResponse("a real response")

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    with real_app.app_context():
        result = complete(messages=[{"role": "user", "content": "Hi"}], model="claude-3-5-sonnet-20241022")

    assert result == "a real response"
    assert captured["model"] == "claude-3-5-sonnet-20241022"
    assert captured["messages"] == [{"role": "user", "content": "Hi"}]
