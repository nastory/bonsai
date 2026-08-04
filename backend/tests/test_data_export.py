"""Tests for full-data export/import (see app/services/data_export.py).

Export is a JSON manifest of every row (generic column-reflection dump, not
a hand-maintained field list) plus the on-disk content files it references,
zipped together. Import is a restore, not a merge: existing courses are
wiped first; UserSettings is the one exception, merged non-secret-fields-only
so API keys already configured on the target installation survive.
"""

import io
import json
import zipfile
from pathlib import Path

import pytest

from app.extensions import db
from app.models import Activity, ConversationMessage, Course, Module, SourceMaterial, UserSettings
from app.services.content_storage import load_activity_content, save_activity_content
from app.services.data_export import DataImportError, export_data, import_data
from app.services.source_material_storage import load_source_material_text, save_source_material_text


def _make_course_with_content(app, course_id="c1") -> Course:
    course = Course(
        id=course_id, title="GPU Programming", description="d", prerequisites=["Python"],
        estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
    )
    module = Module(
        id="m1", course_id=course_id, position=0, title="Basics", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=["Understand GPUs"],
    )
    content_path = save_activity_content("a1", {"body": "Some reading content."})
    activity = Activity(
        id="a1", module_id="m1", position=0, activity_type="reading", title="Intro",
        status="completed", estimated_minutes=10, content_path=content_path,
    )
    module.activities = [activity]
    text_path = save_source_material_text("src1", "Extracted source text.")
    material = SourceMaterial(id="src1", course_id=course_id, file_name="paper.txt", text_path=text_path)
    course.modules = [module]
    course.source_materials = [material]
    db.session.add_all(
        [
            course,
            ConversationMessage(course_id=course_id, role="user", kind="interview_answer", content="I want to learn GPU programming"),
            ConversationMessage(course_id=course_id, module_id="m1", role="assistant", kind="module_learning_digest", content="Covered the basics."),
        ]
    )
    db.session.commit()
    return course


def test_export_data_includes_all_tables(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)

        archive_bytes = export_data()

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            data = json.loads(archive.read("data.json"))

        assert len(data["courses"]) == 1
        assert len(data["modules"]) == 1
        assert len(data["activities"]) == 1
        assert len(data["source_materials"]) == 1
        assert len(data["conversation_messages"]) == 2
        assert "user_settings" in data


def test_export_data_excludes_secret_settings_fields(app, db) -> None:
    with app.app_context():
        settings = UserSettings.get_or_create()
        settings.model_provider_api_key = "sk-secret"
        settings.tavily_api_key = "tvly-secret"
        db.session.commit()

        archive_bytes = export_data()

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            data = json.loads(archive.read("data.json"))

        assert "model_provider_api_key" not in data["user_settings"]
        assert "tavily_api_key" not in data["user_settings"]


def test_export_data_includes_content_files_matching_disk(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)

        archive_bytes = export_data()

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            assert "module_content/a1.json" in names
            assert "source_material_text/src1.txt" in names
            assert json.loads(archive.read("module_content/a1.json")) == {"body": "Some reading content."}
            assert archive.read("source_material_text/src1.txt").decode() == "Extracted source text."


def test_import_data_raises_for_a_non_zip_archive(app, db) -> None:
    with app.app_context():
        with pytest.raises(DataImportError):
            import_data(b"not a zip file")


def test_import_data_round_trips_courses_modules_activities(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)
        archive_bytes = export_data()

        import_data(archive_bytes)

        course = db.session.get(Course, "c1")
        assert course is not None
        assert course.title == "GPU Programming"
        assert course.prerequisites == ["Python"]
        module = db.session.get(Module, "m1")
        assert module is not None
        assert module.title == "Basics"
        activity = db.session.get(Activity, "a1")
        assert activity is not None
        assert activity.status == "completed"
        material = db.session.get(SourceMaterial, "src1")
        assert material is not None


def test_import_data_restores_content_files_that_load_correctly(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)
        archive_bytes = export_data()

        import_data(archive_bytes)

        activity = db.session.get(Activity, "a1")
        assert load_activity_content(activity.content_path) == {"body": "Some reading content."}
        material = db.session.get(SourceMaterial, "src1")
        assert load_source_material_text(material.text_path) == "Extracted source text."


def test_import_data_replaces_rather_than_merges_existing_courses(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app, course_id="original")
        archive_bytes = export_data()  # snapshot with only "original"

        # Now add a second, different course that only exists on "this installation".
        db.session.add(
            Course(
                id="local-only", title="Local Course", description="d", prerequisites=[],
                estimated_timeline="1 week", thumbnail_url="x", stage="active",
            )
        )
        db.session.commit()

        import_data(archive_bytes)

        assert db.session.get(Course, "original") is not None
        assert db.session.get(Course, "local-only") is None


def test_import_data_preserves_existing_api_keys(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)
        archive_bytes = export_data()

        settings = UserSettings.get_or_create()
        settings.model_provider_api_key = "sk-still-here"
        settings.tavily_api_key = "tvly-still-here"
        db.session.commit()

        import_data(archive_bytes)

        settings = UserSettings.get_or_create()
        assert settings.model_provider_api_key == "sk-still-here"
        assert settings.tavily_api_key == "tvly-still-here"


def test_import_data_merges_non_secret_settings_fields(app, db) -> None:
    with app.app_context():
        settings = UserSettings.get_or_create()
        settings.name = "Exported Name"
        settings.feedback_tone = "straightforward"
        db.session.commit()

        archive_bytes = export_data()

        settings.name = "Local Name"
        settings.feedback_tone = "encouraging"
        db.session.commit()

        import_data(archive_bytes)

        settings = UserSettings.get_or_create()
        assert settings.name == "Exported Name"
        assert settings.feedback_tone == "straightforward"


def test_import_data_conversation_messages_get_fresh_ids(app, db) -> None:
    with app.app_context():
        _make_course_with_content(app)
        archive_bytes = export_data()

        import_data(archive_bytes)

        course = db.session.get(Course, "c1")
        contents = {m.content for m in course.conversation}
        assert "I want to learn GPU programming" in contents
        assert "Covered the basics." in contents
        digest = next(m for m in course.conversation if m.kind == "module_learning_digest")
        assert digest.module_id == "m1"
