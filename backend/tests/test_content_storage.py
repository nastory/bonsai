"""Tests for file-based activity content storage.

Per the hybrid storage design: content-heavy generated fields live in a
JSON file on disk (under instance_path), not inline in the database, so a
round trip through save then load should return exactly what was saved.
"""

from pathlib import Path

from app.services.content_storage import delete_activity_content, load_activity_content, save_activity_content


def test_save_activity_content_returns_a_path(app) -> None:
    with app.app_context():
        path = save_activity_content("activity-1", {"body": "Some reading content."})

        assert path.endswith("activity-1.json")


def test_save_activity_content_returns_a_path_relative_to_instance_path(app) -> None:
    # Not absolute: instance_path itself differs between a native run and a
    # container (the same bind-mounted file is /app/instance in Docker but
    # an absolute host path natively), so a stored path must be portable
    # between them rather than baked in as an absolute path.
    with app.app_context():
        path = save_activity_content("activity-1", {"body": "Some reading content."})

        assert not Path(path).is_absolute()


def test_load_activity_content_round_trips_saved_content(app) -> None:
    with app.app_context():
        content = {"question": "Why?", "options": ["A", "B"]}
        path = save_activity_content("activity-2", content)

        loaded = load_activity_content(path)

        assert loaded == content


def test_load_activity_content_still_accepts_a_legacy_absolute_path(app, tmp_path) -> None:
    # Content saved before content_path became instance-relative is still
    # sitting in the database as an absolute path; loading it must keep
    # working rather than silently breaking existing generated content.
    content_file = tmp_path / "legacy-activity.json"
    content_file.write_text('{"body": "legacy content"}')

    with app.app_context():
        loaded = load_activity_content(str(content_file))

    assert loaded == {"body": "legacy content"}


def test_delete_activity_content_removes_the_file(app) -> None:
    with app.app_context():
        path = save_activity_content("activity-3", {"body": "content to delete"})
        absolute_path = Path(app.instance_path) / path
        assert absolute_path.exists()

        delete_activity_content(path)

        assert not absolute_path.exists()


def test_delete_activity_content_is_a_no_op_for_a_missing_file(app) -> None:
    with app.app_context():
        delete_activity_content("module_content/does-not-exist.json")
