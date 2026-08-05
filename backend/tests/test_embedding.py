"""Tests for the LiteLLM embedding wrapper service.

Mirrors test_llm.py's approach: in test mode, no real provider is ever
called; outside test mode, hosted models go through litellm.embedding()
and its response is unwrapped to plain vectors. "ollama/"-prefixed models
bypass litellm entirely (see embed()'s docstring for the confirmed-live
upstream litellm bug this works around) and call Ollama's own /api/embed
endpoint directly via requests.
"""

import pytest
from flask import Flask

from app.services.embedding import MOCK_EMBEDDING_DIM, EmbeddingError, embed


class _FakeEmbeddingItem(dict):
    """A dict subclass so item["embedding"] works, matching litellm's real response shape."""


class _FakeResponse:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.data = [_FakeEmbeddingItem(embedding=v) for v in vectors]


def test_embed_returns_deterministic_fake_vectors_in_test_mode(app: Flask) -> None:
    with app.app_context():
        result = embed(["hello world"], model="text-embedding-3-small")

    assert len(result) == 1
    assert len(result[0]) == MOCK_EMBEDDING_DIM
    assert all(isinstance(v, float) for v in result[0])


def test_embed_is_deterministic_per_text_but_differs_across_texts(app: Flask) -> None:
    with app.app_context():
        first = embed(["a chunk of text"], model="text-embedding-3-small")
        second = embed(["a chunk of text"], model="text-embedding-3-small")
        different = embed(["a different chunk"], model="text-embedding-3-small")

    assert first == second
    assert first != different


def test_embed_does_not_call_litellm_in_test_mode(app: Flask, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("litellm.embedding should not be called in test mode")

    monkeypatch.setattr("app.services.embedding.litellm.embedding", fail_if_called)

    with app.app_context():
        embed(["hello"], model="text-embedding-3-small")


def test_embed_calls_litellm_when_not_in_test_mode(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_embedding(**kwargs):
        captured.update(kwargs)
        return _FakeResponse([[0.1, 0.2, 0.3]])

    monkeypatch.setattr("app.services.embedding.litellm.embedding", fake_embedding)

    with real_app.app_context():
        result = embed(["hello world"], model="text-embedding-3-small", api_key="sk-test")

    assert result == [[0.1, 0.2, 0.3]]
    assert captured["model"] == "text-embedding-3-small"
    assert captured["input"] == ["hello world"]
    assert captured["api_key"] == "sk-test"
    assert "api_base" not in captured


class _FakeHttpResponse:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self._embeddings = embeddings

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"embeddings": self._embeddings}


def test_embed_ollama_model_does_not_call_litellm(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)

    def fail_if_called(**kwargs):
        raise AssertionError("litellm.embedding should not be called for ollama/-prefixed models")

    monkeypatch.setattr("app.services.embedding.litellm.embedding", fail_if_called)
    monkeypatch.setattr(
        "app.services.embedding.requests.post", lambda *a, **k: _FakeHttpResponse([[0.1, 0.2]])
    )

    with real_app.app_context():
        result = embed(["hello"], model="ollama/nomic-embed-text", api_base="http://localhost:11434")

    assert result == [[0.1, 0.2]]


def test_embed_ollama_model_posts_to_the_configured_endpoint(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeHttpResponse([[0.1], [0.2]])

    monkeypatch.setattr("app.services.embedding.requests.post", fake_post)

    with real_app.app_context():
        embed(["a", "b"], model="ollama/nomic-embed-text", api_base="http://localhost:11434")

    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["json"] == {"model": "nomic-embed-text", "input": ["a", "b"]}


def test_embed_ollama_model_raises_embedding_error_on_failure(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)

    def fake_post(*a, **k):
        raise ConnectionError("connection refused")

    monkeypatch.setattr("app.services.embedding.requests.post", fake_post)

    with real_app.app_context(), pytest.raises(EmbeddingError):
        embed(["hello"], model="ollama/nomic-embed-text")


def test_embed_batches_multiple_texts_in_one_call(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_embedding(**kwargs):
        captured.update(kwargs)
        return _FakeResponse([[0.1], [0.2], [0.3]])

    monkeypatch.setattr("app.services.embedding.litellm.embedding", fake_embedding)

    with real_app.app_context():
        result = embed(["a", "b", "c"], model="text-embedding-3-small")

    assert captured["input"] == ["a", "b", "c"]
    assert result == [[0.1], [0.2], [0.3]]
