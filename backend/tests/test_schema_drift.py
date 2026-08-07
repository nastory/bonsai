"""Regression test for data_export.py's generic export/import mechanism.

That mechanism makes exactly two assumptions about every exported model's
schema (see data_export.py's own module docstring): every column is one of
a known-safe set of types (String/Text/Integer/Boolean/JSON/DateTime), and
any DateTime column gets parsed back from its exported isoformat string by
_row_kwargs(). Both assumptions are introspected against the *live* schema
here, not hand-listed, so this test fails the moment a future model change
violates either one - catching drift immediately instead of it surfacing as
a real import crash later.

This is exactly the bug that motivated this file: Activity.completed_at is
a second DateTime column that existed for a while with no import-side
handling, since _row_kwargs() originally only special-cased
ConversationMessage.created_at. Confirmed live: importing a real export
containing a completed activity crashed with "SQLite DateTime type only
accepts Python datetime and date objects as input" - not a subtle bug, an
outright import failure on an extremely common case. Fixed alongside this
test by generalizing _row_kwargs()'s datetime handling to introspect every
model's columns instead of hand-listing one.
"""

from datetime import datetime

from app.extensions import db
from app.models import UserSettings
from app.services.data_export import EXPORTED_MODELS, _row_kwargs

# Column types data_export.py's generic dump (_dump_row)/restore (_row_kwargs)
# mechanism actually knows how to round-trip correctly. String/Text/Integer/
# Boolean/JSON pass straight through unchanged; DateTime is the one type
# that needs explicit isoformat <-> datetime conversion.
KNOWN_SAFE_COLUMN_TYPES = (db.String, db.Text, db.Integer, db.Boolean, db.JSON, db.DateTime)

ALL_EXPORTED_MODELS = [*EXPORTED_MODELS, UserSettings]


def test_every_exported_model_column_is_a_known_safe_type() -> None:
    """Fails if a future model gains a column type the dump/restore mechanism doesn't know how to handle.

    e.g. a Numeric/Decimal, LargeBinary, or Enum column would currently
    round-trip incorrectly (or crash) through the generic dict-of-columns
    dump and datetime-only restore - this is where that shows up, not as a
    real import failure later.
    """
    for model in ALL_EXPORTED_MODELS:
        for column in model.__table__.columns:
            assert isinstance(column.type, KNOWN_SAFE_COLUMN_TYPES), (
                f"{model.__name__}.{column.name} has type {column.type!r}, not one of the types "
                "data_export.py's generic dump/restore actually knows how to round-trip"
            )


def test_every_datetime_column_round_trips_through_row_kwargs() -> None:
    """Fails if a model gains a DateTime column that _row_kwargs() doesn't parse back.

    Discovers DateTime columns by introspecting the live schema
    (model.__table__.columns), not a hand-maintained list, so a future
    DateTime column is covered automatically - the same way _dump_row()'s
    export-side isoformat conversion already is.
    """
    for model in ALL_EXPORTED_MODELS:
        for column in model.__table__.columns:
            if not isinstance(column.type, db.DateTime):
                continue
            exported_row = {column.name: "2026-01-01T12:00:00"}

            kwargs = _row_kwargs(model, exported_row)

            assert isinstance(kwargs[column.name], datetime), (
                f"{model.__name__}.{column.name} is a DateTime column but _row_kwargs() left it as "
                f"{kwargs[column.name]!r} instead of parsing it back to a real datetime"
            )
