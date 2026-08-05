"""Wraps LiteLLM's image generation call, mirroring embedding.py's conventions.

A separate module from llm.py/embedding.py since image generation is yet
another distinct model role (see model_selection.py's
resolve_image_generation_config()) with its own LiteLLM entrypoint
(litellm.image_generation(), not completion() or embedding()) and response
shape.
"""

import base64

import litellm
from flask import current_app

# A real, valid 1x1 transparent PNG - not a fake string - so the storage/
# serving path (which expects real image bytes) is genuinely exercised in
# test mode, same spirit as every other LLM_TEST_MODE mock returning a
# real-shaped value rather than a placeholder that would break downstream code.
_MOCK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ImageGenerationError(Exception):
    """Raised when an image generation call fails."""


def generate_thumbnail_image(prompt: str, model_config: dict) -> bytes:
    """Generate a single thumbnail image.

    Args:
        prompt: A short description of what the image should depict (e.g.
            built from the course's title/description).
        model_config: The dict from resolve_image_generation_config() -
            "model" plus optional "api_key"/"api_base".

    Returns:
        The generated image's raw bytes (PNG). Returns a small fixed
        placeholder image instead of calling a real provider when
        ``LLM_TEST_MODE`` is set, matching every other generation
        function's mock-branch convention.

    Raises:
        ImageGenerationError: If the generation call fails, or the
            response doesn't include image data.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return _MOCK_PNG_BYTES

    kwargs: dict = {"prompt": prompt, "response_format": "b64_json", "size": "1024x1024", **model_config}

    try:
        response = litellm.image_generation(**kwargs)
        b64_data = response.data[0]["b64_json"]
    except Exception as e:
        raise ImageGenerationError(f"Image generation call failed: {e}") from e

    if not b64_data:
        raise ImageGenerationError("Image generation response had no image data.")
    return base64.b64decode(b64_data)
