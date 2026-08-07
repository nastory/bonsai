"""Export/import of a learner's full Bonsai data as a single portable archive.

Per the PRD: course outlines, module content, progress, and settings —
never API keys or other credentials. Bonsai is single-user/single-installation
(no auth, no multi-tenancy), so this operates on the entire database, not a
filtered subset.

Every model in this schema uses only String/Text/Integer/Boolean/JSON/DateTime
columns. That's what makes a *generic* column-reflection dump/restore
(iterate model.__table__.columns) the right approach here, rather than
hand-listing fields per model: it survives future schema changes without
needing to stay in sync by hand. DateTime is the one type that needs real
conversion (isoformat string <-> datetime), and _row_kwargs() below
introspects the live schema for it rather than hand-listing which columns
are DateTime - a hand-listed version of this once only covered
ConversationMessage.created_at, silently missing Activity.completed_at
(a real bug, confirmed live: importing an export with a completed activity
crashed) until test_schema_drift.py caught it. That test enforces both of
this paragraph's claims against the live schema, so it fails immediately if
either stops being true, instead of a real import crashing on it later.
"""

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from flask import current_app

from app.extensions import db
from app.models import Activity, ConversationMessage, Course, Module, SourceMaterial, UserSettings
from app.services.content_storage import delete_activity_content
from app.services.source_material_storage import delete_source_material_text

DATA_FILENAME = "data.json"
CONTENT_SUBDIRS = ["module_content", "source_material_text"]
# Order matters for import: each model's foreign keys must already exist,
# so parents are restored before children.
EXPORTED_MODELS = [Course, Module, Activity, SourceMaterial, ConversationMessage]
SECRET_USER_SETTINGS_FIELDS = {"model_provider_api_key", "tavily_api_key"}


class DataImportError(Exception):
    """Raised when an uploaded archive isn't a valid Bonsai export."""


def _dump_row(instance: db.Model) -> dict:
    row = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        row[column.name] = value
    return row


def export_data() -> bytes:
    """Build a downloadable .zip archive of everything except credentials.

    Returns:
        The archive's raw bytes: one data.json manifest (every row of every
        EXPORTED_MODELS table, plus non-secret UserSettings fields) and a
        copy of every on-disk content file the manifest references
        (module_content/, source_material_text/).
    """
    data: dict = {
        model.__tablename__: [_dump_row(row) for row in db.session.execute(db.select(model)).scalars()]
        for model in EXPORTED_MODELS
    }
    settings_row = UserSettings.get_or_create()
    data["user_settings"] = {
        key: value for key, value in _dump_row(settings_row).items() if key not in SECRET_USER_SETTINGS_FIELDS
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DATA_FILENAME, json.dumps(data, indent=2))
        for subdir in CONTENT_SUBDIRS:
            directory = Path(current_app.instance_path) / subdir
            if not directory.is_dir():
                continue
            for file in directory.iterdir():
                if file.is_file():
                    archive.write(file, arcname=f"{subdir}/{file.name}")
    return buffer.getvalue()


def _row_kwargs(model: type[db.Model], row: dict) -> dict:
    kwargs = dict(row)
    # Generic, not hand-listed per model/column - the same reasoning as
    # _dump_row()'s isoformat conversion (which already handles any
    # DateTime column, not just ConversationMessage.created_at): a new
    # DateTime column added to any model (e.g. Activity.completed_at) is
    # parsed back automatically, no import-side special-casing to
    # remember. See test_schema_drift.py for the regression test this keeps
    # honest against future schema changes.
    for column in model.__table__.columns:
        if isinstance(column.type, db.DateTime) and kwargs.get(column.name):
            kwargs[column.name] = datetime.fromisoformat(kwargs[column.name])
    if model is ConversationMessage:
        # Auto-increment, and nothing else has a foreign key pointing at it
        # by value, so a fresh id from this installation's own sequence is
        # fine — trying to force back the exported id risks colliding with
        # rows that already exist here.
        kwargs.pop("id", None)
    return kwargs


def import_data(archive_bytes: bytes) -> None:
    """Replace all courses/progress with what's in a previously exported archive.

    This is a restore, not a merge: every existing Course (and, via cascade,
    its Modules/Activities/SourceMaterials/ConversationMessages, plus their
    on-disk content files) is deleted first, the same way delete_course()
    already does it. Avoids any ambiguity about id collisions between what's
    already here and what's being restored.

    UserSettings is different: only non-secret fields are overwritten on the
    existing single row. Whatever API keys are already configured on *this*
    installation are left completely untouched, since the archive never had
    them to begin with (see export_data()) — re-importing onto an
    already-configured installation shouldn't force re-entering keys that
    still work.

    Args:
        archive_bytes: The raw bytes of a previously exported .zip archive.

    Raises:
        DataImportError: If the archive isn't a valid Bonsai export.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            data = json.loads(archive.read(DATA_FILENAME))
            content_files = {
                name: archive.read(name) for name in archive.namelist() if name != DATA_FILENAME
            }
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
        raise DataImportError(f"Not a valid Bonsai export archive: {e}") from e

    for course in db.session.execute(db.select(Course)).scalars():
        for module in course.modules:
            for activity in module.activities:
                if activity.content_path:
                    delete_activity_content(activity.content_path)
        for material in course.source_materials:
            delete_source_material_text(material.text_path)
        db.session.delete(course)
    db.session.flush()

    for model in EXPORTED_MODELS:
        for row in data.get(model.__tablename__, []):
            db.session.add(model(**_row_kwargs(model, row)))

    settings = UserSettings.get_or_create()
    for key, value in data.get("user_settings", {}).items():
        if key not in SECRET_USER_SETTINGS_FIELDS and key != "id":
            setattr(settings, key, value)

    for name, content in content_files.items():
        absolute_path = Path(current_app.instance_path) / name
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)

    db.session.commit()
