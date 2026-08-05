"""Tests for the single-row UserSettings model."""

from app.models import UserSettings


def test_get_or_create_returns_defaults_on_first_call(db) -> None:
    settings = UserSettings.get_or_create()

    assert settings.id == 1
    assert settings.feedback_tone == "encouraging"
    assert settings.thumbnail_generation_enabled is True
    assert settings.model_provider_tier == "hosted"
    assert settings.deep_search_enabled is False
    assert settings.visual_aids_enabled is False
    assert settings.video_embedding_enabled is False
    assert settings.weekly_goal_activities is None
    assert settings.image_generation_model is None
    assert settings.image_generation_use_completion_credentials is True


def test_get_or_create_returns_the_same_row_on_subsequent_calls(db) -> None:
    first = UserSettings.get_or_create()
    first.name = "Nigel Story"
    db.session.commit()

    second = UserSettings.get_or_create()

    assert second.id == first.id
    assert second.name == "Nigel Story"
