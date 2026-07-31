"""Flask application factory for the Bonsai backend."""

import os

from flask import Flask
from flask_cors import CORS

from app.extensions import db, migrate
from app.routes.activities import activities_bp
from app.routes.course_creation import course_creation_bp
from app.routes.courses import courses_bp
from app.routes.health import health_bp
from app.routes.modules import modules_bp
from app.routes.settings import settings_bp


def create_app(test: bool = False, in_memory_db: bool = False) -> Flask:
    """Build and configure the Flask app.

    Args:
        test: When True, sets ``LLM_TEST_MODE`` in the app config so that
            LLM (and eventually retrieval) calls return canned responses
            instead of hitting a real provider. Used for local development
            without an API key and for the automated test suite.
        in_memory_db: When True, points the database at an in-memory SQLite
            instance instead of the real data file. Independent of `test`:
            day-to-day development wants mocked LLM calls against your real,
            persistent data, while the automated test suite wants both
            mocked calls and a throwaway database.

    Returns:
        A configured Flask application with CORS, the database, and all
        blueprints registered.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config["LLM_TEST_MODE"] = test

    # Always needed, independent of in_memory_db: generated activity content
    # (see app/services/content_storage.py) lives on disk under instance_path
    # even when the database itself is an in-memory throwaway.
    os.makedirs(app.instance_path, exist_ok=True)

    if in_memory_db:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        db_path = os.path.join(app.instance_path, "bonsai.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  registers tables with db.metadata

    app.register_blueprint(health_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(course_creation_bp)
    app.register_blueprint(modules_bp)

    return app
