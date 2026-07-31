"""Flask application factory for the Bonsai backend."""

import os

from flask import Flask
from flask_cors import CORS

from app.extensions import db, migrate
from app.routes.health import health_bp


def create_app(test: bool = False) -> Flask:
    """Build and configure the Flask app.

    Args:
        test: When True, sets ``LLM_TEST_MODE`` in the app config so that
            LLM (and eventually retrieval) calls return canned responses
            instead of hitting a real provider, and points the database at
            an in-memory SQLite instance instead of the real data file.
            Used both for local development without an API key and for the
            automated test suite.

    Returns:
        A configured Flask application with CORS, the database, and all
        blueprints registered.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config["LLM_TEST_MODE"] = test

    if test:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    else:
        os.makedirs(app.instance_path, exist_ok=True)
        db_path = os.path.join(app.instance_path, "bonsai.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  registers tables with db.metadata

    app.register_blueprint(health_bp)

    return app
