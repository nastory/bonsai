"""Resolves the learner's UserSettings into kwargs for llm.complete().

A separate module from course_generation.py since module-content generation
will need the exact same resolution logic.
"""

from app.models import UserSettings

DEFAULT_HOSTED_MODELS = {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o",
}
DEFAULT_BYOM_MODEL = "llama3"
DEFAULT_BYOM_ENDPOINT = "http://localhost:11434"


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
