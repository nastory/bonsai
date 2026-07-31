"""Tests for create_app()'s test-mode and database-selection flags.

LLM_TEST_MODE (mocked LLM calls) and using an in-memory database are
independent concerns: you can want mocked LLM calls against your real,
persistent data during day-to-day development, or a fresh in-memory
database for the automated test suite. This pins down that create_app's
`test` flag alone does not silently switch away from the real database.
"""

from app import create_app


def test_test_mode_alone_still_uses_the_real_database_file() -> None:
    app = create_app(test=True)

    assert app.config["LLM_TEST_MODE"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite:///:memory:"
    assert "bonsai.db" in app.config["SQLALCHEMY_DATABASE_URI"]


def test_in_memory_db_flag_switches_to_an_in_memory_database() -> None:
    app = create_app(test=True, in_memory_db=True)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_default_create_app_uses_neither_test_mode_nor_in_memory_db() -> None:
    app = create_app()

    assert app.config["LLM_TEST_MODE"] is False
    assert app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite:///:memory:"
