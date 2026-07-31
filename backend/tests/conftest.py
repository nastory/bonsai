"""Shared pytest fixtures for the Bonsai backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app() -> Flask:
    """A Flask app instance in test mode (mocked LLM calls, no real API costs)."""
    return create_app(test=True)


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
