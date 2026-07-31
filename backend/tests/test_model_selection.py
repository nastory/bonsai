"""Tests for resolving a learner's UserSettings into LiteLLM call kwargs."""

from app.models import UserSettings
from app.services.model_selection import resolve_model_config


def test_resolve_model_config_defaults_to_anthropic_when_nothing_configured(db) -> None:
    UserSettings.get_or_create()

    config = resolve_model_config()

    assert config["model"] == "claude-3-5-sonnet-20241022"
    assert "api_key" not in config
    assert "api_base" not in config


def test_resolve_model_config_uses_configured_hosted_model_and_key(db) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "hosted"
    settings.model_provider_hosted_provider = "openai"
    settings.model_provider_hosted_model = "gpt-4o-mini"
    settings.model_provider_api_key = "sk-test"

    config = resolve_model_config()

    assert config["model"] == "gpt-4o-mini"
    assert config["api_key"] == "sk-test"


def test_resolve_model_config_defaults_openai_model_when_blank(db) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "hosted"
    settings.model_provider_hosted_provider = "openai"

    config = resolve_model_config()

    assert config["model"] == "gpt-4o"


def test_resolve_model_config_uses_byom_endpoint_and_model(db) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "byom"
    settings.model_provider_byom_endpoint = "http://localhost:11434"
    settings.model_provider_byom_model = "llama3"

    config = resolve_model_config()

    assert config["model"] == "ollama/llama3"
    assert config["api_base"] == "http://localhost:11434"
    assert "api_key" not in config


def test_resolve_model_config_byom_falls_back_to_default_endpoint_and_model(db) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "byom"

    config = resolve_model_config()

    assert config["model"] == "ollama/llama3"
    assert config["api_base"] == "http://localhost:11434"
