"""Shared pytest fixtures for the Bonsai backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app() -> Flask:
    """A Flask app instance in test mode: mocked LLM calls and a throwaway in-memory database."""
    return create_app(test=True, in_memory_db=True)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """A test client for making requests against the app fixture."""
    return app.test_client()


@pytest.fixture
def db(app: Flask):
    """A fresh in-memory database with tables created, torn down after each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def real_llm_app() -> Flask:
    """A Flask app with real (non-mocked) LLM calls, but still an isolated in-memory database.

    For tests that need to monkeypatch litellm.completion directly to
    exercise the real complete()/validation code path, rather than the
    LLM_TEST_MODE canned-response branches.
    """
    app = create_app(test=False, in_memory_db=True)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def real_llm_client(real_llm_app: Flask) -> FlaskClient:
    """A test client for the real_llm_app fixture."""
    return real_llm_app.test_client()
