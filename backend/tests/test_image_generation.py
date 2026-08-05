"""Tests for the LiteLLM image generation wrapper service.

Mirrors test_embedding.py's approach: in test mode, no real provider is
ever called; outside test mode, litellm.image_generation() is called and
its b64_json response is decoded to raw bytes. No live OpenAI call is made
here (see the "Course thumbnail image generation" plan) - the real-mode
test below only proves the correct request gets built and the response
gets unwrapped correctly, via a monkeypatched litellm.image_generation.
"""

import base64

import pytest

from app.services.image_generation import ImageGenerationError, generate_thumbnail_image


class _FakeImageItem(dict):
    """A dict subclass so item["b64_json"] works, matching litellm's real response shape."""


class _FakeResponse:
    def __init__(self, b64_json: str) -> None:
        self.data = [_FakeImageItem(b64_json=b64_json)]


def test_generate_thumbnail_image_returns_real_png_bytes_in_test_mode(app) -> None:
    with app.app_context():
        result = generate_thumbnail_image("a course about GPU programming", {"model": "dall-e-3"})

    assert result.startswith(b"\x89PNG\r\n\x1a\n")


def test_generate_thumbnail_image_does_not_call_litellm_in_test_mode(app, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("litellm.image_generation should not be called in test mode")

    monkeypatch.setattr("app.services.image_generation.litellm.image_generation", fail_if_called)

    with app.app_context():
        generate_thumbnail_image("a course about GPU programming", {"model": "dall-e-3"})


def test_generate_thumbnail_image_calls_litellm_when_not_in_test_mode(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}
    fake_bytes = b"fake-image-bytes"
    fake_b64 = base64.b64encode(fake_bytes).decode()

    def fake_image_generation(**kwargs):
        captured.update(kwargs)
        return _FakeResponse(fake_b64)

    monkeypatch.setattr("app.services.image_generation.litellm.image_generation", fake_image_generation)

    with real_app.app_context():
        result = generate_thumbnail_image("a course about GPU programming", {"model": "dall-e-3", "api_key": "sk-test"})

    assert result == fake_bytes
    assert captured["model"] == "dall-e-3"
    assert captured["api_key"] == "sk-test"
    assert captured["prompt"] == "a course about GPU programming"
    assert captured["response_format"] == "b64_json"


def test_generate_thumbnail_image_raises_on_litellm_failure(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)

    def fail(**kwargs):
        raise ConnectionError("connection refused")

    monkeypatch.setattr("app.services.image_generation.litellm.image_generation", fail)

    with real_app.app_context(), pytest.raises(ImageGenerationError):
        generate_thumbnail_image("a course about GPU programming", {"model": "dall-e-3"})


def test_generate_thumbnail_image_raises_when_response_has_no_image_data(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)

    monkeypatch.setattr(
        "app.services.image_generation.litellm.image_generation",
        lambda **kwargs: _FakeResponse(""),
    )

    with real_app.app_context(), pytest.raises(ImageGenerationError):
        generate_thumbnail_image("a course about GPU programming", {"model": "dall-e-3"})
