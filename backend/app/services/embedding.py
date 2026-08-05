"""Wraps LiteLLM's embedding call, mirroring llm.py's complete() conventions.

A separate module from llm.py since embeddings are a distinct model role
(see model_selection.py's resolve_embedding_config()) with a different
LiteLLM entrypoint (litellm.embedding(), not litellm.completion()) and
response shape.
"""

import random

import litellm
import requests
from flask import current_app

MOCK_EMBEDDING_DIM = 16
REQUEST_TIMEOUT_SECONDS = 60  # a batch of many chunks can take a while on CPU-only local Ollama
DEFAULT_OLLAMA_API_BASE = "http://localhost:11434"


class EmbeddingError(Exception):
    """Raised when an embedding call fails."""


def embed(texts: list[str], model: str, api_key: str | None = None, api_base: str | None = None) -> list[list[float]]:
    """Embed a batch of texts in one call.

    Args:
        texts: The texts to embed, e.g. chunk bodies or a retrieval query.
        model: The LiteLLM-recognized embedding model identifier (e.g.
            "text-embedding-3-small" for a hosted model, or
            "ollama/nomic-embed-text" for a local one - see
            resolve_embedding_config()'s docstring for why "ollama/", not
            "ollama_chat/").
        api_key: The provider API key, for hosted models.
        api_base: The provider's base URL, for BYOM/local models.

    Returns:
        One embedding vector per input text, same order. Returns small
        deterministic fake vectors instead of calling a real provider when
        ``LLM_TEST_MODE`` is set, matching every other generation
        function's mock-branch convention.

    Raises:
        EmbeddingError: If the embedding call fails.
    """
    if current_app.config.get("LLM_TEST_MODE"):
        return [_mock_embedding(text) for text in texts]

    if model.startswith("ollama/"):
        # Bypasses litellm.embedding() for Ollama specifically: confirmed
        # live against a real Ollama instance that the installed
        # litellm==1.56.4's sync Ollama embeddings path
        # (llms/ollama/completion/handler.py's ollama_embeddings, which
        # wraps its own async ollama_aembeddings via asyncio.run()) raises
        # `TypeError: object dict can't be used in 'await' expression` -
        # a real upstream bug, not a config/prefix mistake (unlike the
        # ollama_chat/ completions fix, which *was* a prefix mistake).
        # Ollama's own /api/embed endpoint is simple and well-documented,
        # so calling it directly avoids depending on a fix landing upstream.
        return _embed_via_ollama(texts, model.removeprefix("ollama/"), api_base)

    kwargs: dict = {"model": model, "input": texts}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = litellm.embedding(**kwargs)
    return [item["embedding"] for item in response.data]


def _embed_via_ollama(texts: list[str], model: str, api_base: str | None) -> list[list[float]]:
    base = (api_base or DEFAULT_OLLAMA_API_BASE).rstrip("/")
    try:
        response = requests.post(
            f"{base}/api/embed", json={"model": model, "input": texts}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()["embeddings"]
    except Exception as e:
        raise EmbeddingError(f"Ollama embedding call failed: {e}") from e


def _mock_embedding(text: str) -> list[float]:
    # random.Random(text) seeds deterministically off the string itself
    # (not Python's randomized hash()), so this is stable across runs/tests
    # without needing any real semantic meaning - test mode only needs to
    # exercise the embed -> index -> query plumbing, not real retrieval.
    rng = random.Random(text)
    return [rng.random() for _ in range(MOCK_EMBEDDING_DIM)]
