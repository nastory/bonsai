"""Integration test: course generation actually uses the configured model/provider.

Runs with LLM_TEST_MODE off (real_llm_app fixture) so the real complete() ->
resolve_model_config() path is exercised, with litellm.completion monkeypatched
to capture what it was called with rather than making a network call.
"""

from app.models import UserSettings
from app.services.course_generation import start_course


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def test_start_course_calls_litellm_with_byom_settings(real_llm_app, monkeypatch) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "byom"
    settings.model_provider_byom_endpoint = "http://localhost:11434"
    settings.model_provider_byom_model = "llama3"

    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _FakeResponse('{"done": false, "question": "What is your experience level?"}')

    monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

    start_course("I want to learn GPU programming")

    assert captured["model"] == "ollama/llama3"
    assert captured["api_base"] == "http://localhost:11434"
    assert "api_key" not in captured
