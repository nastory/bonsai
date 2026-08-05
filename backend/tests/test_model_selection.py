"""Tests for resolving a learner's UserSettings into LiteLLM call kwargs."""

import pytest

from app.models import UserSettings
from app.services.model_selection import (
    EmbeddingNotConfiguredError,
    ImageGenerationNotConfiguredError,
    resolve_embedding_config,
    resolve_image_generation_config,
    resolve_model_config,
)


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

    assert config["model"] == "ollama_chat/llama3"
    assert config["api_base"] == "http://localhost:11434"
    assert "api_key" not in config


def test_resolve_model_config_byom_falls_back_to_default_endpoint_and_model(db) -> None:
    settings = UserSettings.get_or_create()
    settings.model_provider_tier = "byom"

    config = resolve_model_config()

    assert config["model"] == "ollama_chat/llama3"
    assert config["api_base"] == "http://localhost:11434"


def test_resolve_embedding_config_defaults_to_a_mock_model_in_test_mode(db) -> None:
    UserSettings.get_or_create()

    # LLM_TEST_MODE (the `db`/`app` fixtures' mode): embedding.embed()'s mock
    # branch never looks at the model name, so requiring real configuration
    # here would just be friction, not a meaningful check - see
    # resolve_embedding_config()'s docstring.
    config = resolve_embedding_config()

    assert config["model"]


def test_resolve_embedding_config_raises_when_no_embedding_model_configured(real_llm_app) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create()

        with pytest.raises(EmbeddingNotConfiguredError):
            resolve_embedding_config()


def test_resolve_embedding_config_byom_uses_ollama_prefix_and_completion_endpoint(real_llm_app) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.model_provider_tier = "byom"
        settings.model_provider_byom_endpoint = "http://localhost:11434"
        settings.embedding_model = "nomic-embed-text"

        config = resolve_embedding_config()

    assert config["model"] == "ollama/nomic-embed-text"
    assert config["api_base"] == "http://localhost:11434"
    assert "api_key" not in config


def test_resolve_embedding_config_hosted_reuses_completion_credentials_by_default(real_llm_app) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.model_provider_tier = "hosted"
        settings.model_provider_api_key = "sk-completion"
        settings.embedding_model = "text-embedding-3-small"

        config = resolve_embedding_config()

    assert config["model"] == "text-embedding-3-small"
    assert config["api_key"] == "sk-completion"


def test_resolve_embedding_config_hosted_uses_dedicated_key_when_not_reusing_credentials(real_llm_app) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.model_provider_tier = "hosted"
        settings.model_provider_api_key = "sk-completion"
        settings.embedding_model = "text-embedding-3-small"
        settings.embedding_use_completion_credentials = False
        settings.embedding_api_key = "sk-embedding"

        config = resolve_embedding_config()

    assert config["api_key"] == "sk-embedding"


def test_resolve_image_generation_config_defaults_to_a_mock_model_in_test_mode(db) -> None:
    UserSettings.get_or_create()

    config = resolve_image_generation_config()

    assert config["model"]


def test_resolve_image_generation_config_raises_when_not_configured(real_llm_app) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create()

        with pytest.raises(ImageGenerationNotConfiguredError):
            resolve_image_generation_config()


def test_resolve_image_generation_config_hosted_reuses_completion_credentials_by_default(real_llm_app) -> None:
    # Tier branching (BYOM/hosted-shared/hosted-dedicated) mirrors
    # resolve_embedding_config() exactly (see the docstring) and is fully
    # exercised by that function's own tests above - this just proves the
    # image-generation-specific model field routes through correctly.
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.model_provider_tier = "hosted"
        settings.model_provider_api_key = "sk-completion"
        settings.image_generation_model = "dall-e-3"

        config = resolve_image_generation_config()

    assert config["model"] == "dall-e-3"
    assert config["api_key"] == "sk-completion"
