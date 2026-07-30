"""Flask application factory for the Bonsai backend."""

from flask import Flask
from flask_cors import CORS

from app.routes.health import health_bp


def create_app() -> Flask:
    """Build and configure the Flask app.

    Returns:
        A configured Flask application with CORS enabled and all
        blueprints registered.
    """
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(health_bp)

    return app
