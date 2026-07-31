"""Tests for the Tavily-backed retrieval wrapper.

Mirrors llm.py's LLM_TEST_MODE convention: with it on, these return canned
results without ever calling requests.post, so retrieval never costs API
credits during day-to-day development or the test suite.
"""

import pytest
from flask import Flask

from app.services.retrieval import RetrievalError, fetch_page, web_search


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_web_search_returns_canned_results_in_test_mode(app: Flask) -> None:
    with app.app_context():
        results = web_search("GPU programming", api_key="tvly-test")

    assert len(results) >= 1
    assert all({"title", "url", "content"} <= result.keys() for result in results)


def test_web_search_does_not_call_requests_in_test_mode(app: Flask, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("requests.post should not be called in test mode")

    monkeypatch.setattr("app.services.retrieval.requests.post", fail_if_called)

    with app.app_context():
        web_search("GPU programming", api_key="tvly-test")


def test_web_search_calls_tavily_and_parses_results(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(
            200,
            {"results": [{"title": "A GPU Primer", "url": "https://example.com/gpu", "content": "GPUs are..."}]},
        )

    monkeypatch.setattr("app.services.retrieval.requests.post", fake_post)

    with real_app.app_context():
        results = web_search("GPU programming", api_key="tvly-real", max_results=3)

    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["json"] == {"api_key": "tvly-real", "query": "GPU programming", "max_results": 3}
    assert results == [{"title": "A GPU Primer", "url": "https://example.com/gpu", "content": "GPUs are..."}]


def test_web_search_raises_retrieval_error_on_http_failure(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    monkeypatch.setattr(
        "app.services.retrieval.requests.post", lambda *a, **kw: _FakeResponse(401, {"error": "bad key"})
    )

    with real_app.app_context(), pytest.raises(RetrievalError):
        web_search("GPU programming", api_key="bad-key")


def test_fetch_page_returns_canned_content_in_test_mode(app: Flask) -> None:
    with app.app_context():
        result = fetch_page("https://example.com/gpu", api_key="tvly-test")

    assert result["url"] == "https://example.com/gpu"
    assert "content" in result


def test_fetch_page_calls_tavily_and_parses_content(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    captured: dict = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(200, {"results": [{"url": "https://example.com/gpu", "raw_content": "Full text."}]})

    monkeypatch.setattr("app.services.retrieval.requests.post", fake_post)

    with real_app.app_context():
        result = fetch_page("https://example.com/gpu", api_key="tvly-real")

    assert captured["url"] == "https://api.tavily.com/extract"
    assert captured["json"] == {"api_key": "tvly-real", "urls": ["https://example.com/gpu"]}
    assert result == {"url": "https://example.com/gpu", "content": "Full text."}


def test_fetch_page_raises_retrieval_error_when_no_results(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False)
    monkeypatch.setattr("app.services.retrieval.requests.post", lambda *a, **kw: _FakeResponse(200, {"results": []}))

    with real_app.app_context(), pytest.raises(RetrievalError):
        fetch_page("https://example.com/gpu", api_key="tvly-real")
