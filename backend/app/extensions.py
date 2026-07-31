"""Shared Flask extension instances.

Kept separate from create_app() and models.py to avoid circular imports:
models import `db` from here, and create_app() calls `db.init_app(app)`.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
