"""Resolves the learner's UserSettings into kwargs for llm.complete().

A separate module from course_generation.py since module-content generation
will need the exact same resolution logic.
"""

from flask import current_app

from app.models import UserSettings

DEFAULT_HOSTED_MODELS = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o",
}
DEFAULT_BYOM_MODEL = "llama3"
DEFAULT_BYOM_ENDPOINT = "http://localhost:11434"
MOCK_EMBEDDING_MODEL = "mock-embedding-model"


class EmbeddingNotConfiguredError(Exception):
    """Raised when document-grounded generation needs an embedding model but none is set.

    Unlike the completion model (which has a sensible universal default per
    tier - see DEFAULT_HOSTED_MODELS/DEFAULT_BYOM_MODEL), there's no safe
    default embedding model to guess: a hosted-tier default wouldn't be a
    valid model name for BYOM/Ollama and vice versa. Failing clearly here,
    with an actionable message, is more honest than silently picking a
    default that's likely wrong for the learner's configured tier.
    """


def resolve_model_config() -> dict:
    """Build the model/api_key/api_base kwargs llm.complete() needs.

    Reads the single UserSettings row to decide, based on the configured
    tier, which model to call and how to reach it: a hosted provider
    (with its API key) or a BYOM endpoint (LiteLLM's "ollama_chat/<model>"
    convention, with an api_base). Deliberately "ollama_chat/", not the
    plain "ollama/" prefix: the latter routes through Ollama's older
    /api/generate endpoint, which (in the installed litellm version) breaks
    when combined with llm.complete()'s JSON response_format — confirmed
    against a real local Ollama instance. "ollama_chat/" uses /api/chat,
    the endpoint actually meant for chat-shaped messages, and works
    correctly with JSON mode.

    Returns:
        A dict with a "model" key, plus "api_key" (hosted) or "api_base"
        (BYOM) when relevant. Keys are omitted rather than set to None,
        so llm.complete() doesn't forward a meaningless value.
    """
    settings = UserSettings.get_or_create()

    if settings.model_provider_tier == "byom":
        model_name = settings.model_provider_byom_model or DEFAULT_BYOM_MODEL
        endpoint = settings.model_provider_byom_endpoint or DEFAULT_BYOM_ENDPOINT
        return {"model": f"ollama_chat/{model_name}", "api_base": endpoint}

    hosted_provider = settings.model_provider_hosted_provider or "anthropic"
    default_model = DEFAULT_HOSTED_MODELS.get(hosted_provider, DEFAULT_HOSTED_MODELS["anthropic"])
    model_name = settings.model_provider_hosted_model or default_model

    config: dict = {"model": model_name}
    if settings.model_provider_api_key:
        config["api_key"] = settings.model_provider_api_key
    return config


def resolve_embedding_config() -> dict:
    """Build the model/api_key/api_base kwargs embedding.embed() needs.

    Mirrors resolve_model_config()'s tier branch, but for the embedding
    model role instead of completion. Deliberately "ollama/", not
    "ollama_chat/": confirmed against the installed litellm version's
    source (litellm/main.py's embedding()) that it only has a plain
    "ollama" provider branch - "ollama_chat" doesn't exist for embeddings,
    it's specifically the chat-completions routing fix from
    resolve_model_config(). Using it here would silently fail to match any
    provider branch.

    BYOM reuses the completion model's endpoint (one local Ollama instance
    serving both chat and embedding models is the common case, and there's
    no separate embedding endpoint setting). Hosted reuses the completion
    model's API key unless the learner has opted into a separate one via
    UserSettings.embedding_use_completion_credentials.

    Returns:
        A dict with a "model" key, plus "api_key" (hosted) or "api_base"
        (BYOM) when relevant, same convention as resolve_model_config().

    Raises:
        EmbeddingNotConfiguredError: If no embedding model is set. Not
            raised in LLM_TEST_MODE - embedding.embed()'s mock branch never
            looks at the model name, so requiring real configuration in
            tests would just be friction, not a meaningful check.
    """
    settings = UserSettings.get_or_create()
    if current_app.config.get("LLM_TEST_MODE"):
        return {"model": settings.embedding_model or MOCK_EMBEDDING_MODEL}

    if not settings.embedding_model:
        raise EmbeddingNotConfiguredError(
            "No embedding model is configured. Set one in Settings to use document-grounded courses."
        )
    model_name = settings.embedding_model

    if settings.model_provider_tier == "byom":
        endpoint = settings.model_provider_byom_endpoint or DEFAULT_BYOM_ENDPOINT
        return {"model": f"ollama/{model_name}", "api_base": endpoint}

    config: dict = {"model": model_name}
    api_key = (
        settings.model_provider_api_key
        if settings.embedding_use_completion_credentials
        else settings.embedding_api_key
    )
    if api_key:
        config["api_key"] = api_key
    return config
