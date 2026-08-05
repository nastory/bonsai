"""Routes for the learner's app-wide settings (a single row, not per-user)."""

from flask import Blueprint, jsonify, request
from flask.wrappers import Response

from app.extensions import db
from app.models import UserSettings

settings_bp = Blueprint("settings", __name__)


@settings_bp.get("/api/settings")
def get_settings() -> Response:
    """Get the learner's current settings, creating defaults on first use.

    Returns:
        The serialized settings.
    """
    settings = UserSettings.get_or_create()
    return jsonify(settings.to_dict())


@settings_bp.put("/api/settings")
def update_settings() -> Response:
    """Update the learner's settings.

    Only fields present in the request body are changed. Anything omitted,
    including individual modelProvider sub-fields like apiKey, keeps its
    current stored value rather than being cleared.

    Returns:
        The serialized settings after the update.
    """
    settings = UserSettings.get_or_create()
    body = request.get_json(force=True) or {}

    if "name" in body:
        settings.name = body["name"]
    if "feedbackTone" in body:
        settings.feedback_tone = body["feedbackTone"]
    if "thumbnailGenerationEnabled" in body:
        settings.thumbnail_generation_enabled = body["thumbnailGenerationEnabled"]
    if "embeddingModel" in body:
        settings.embedding_model = body["embeddingModel"]
    if "embeddingUseCompletionCredentials" in body:
        settings.embedding_use_completion_credentials = body["embeddingUseCompletionCredentials"]
    if "embeddingApiKey" in body:
        settings.embedding_api_key = body["embeddingApiKey"]
    if "tavilyApiKey" in body:
        settings.tavily_api_key = body["tavilyApiKey"]
    if "deepSearchEnabled" in body:
        settings.deep_search_enabled = body["deepSearchEnabled"]

    model_provider = body.get("modelProvider", {})
    if "tier" in model_provider:
        settings.model_provider_tier = model_provider["tier"]
    if "hostedProvider" in model_provider:
        settings.model_provider_hosted_provider = model_provider["hostedProvider"]
    if "hostedModel" in model_provider:
        settings.model_provider_hosted_model = model_provider["hostedModel"]
    if "byomEndpoint" in model_provider:
        settings.model_provider_byom_endpoint = model_provider["byomEndpoint"]
    if "byomModel" in model_provider:
        settings.model_provider_byom_model = model_provider["byomModel"]
    if "apiKey" in model_provider:
        settings.model_provider_api_key = model_provider["apiKey"]

    db.session.commit()
    return jsonify(settings.to_dict())
