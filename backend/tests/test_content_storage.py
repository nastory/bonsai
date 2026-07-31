"""Tests for file-based activity content storage.

Per the hybrid storage design: content-heavy generated fields live in a
JSON file on disk (under instance_path), not inline in the database, so a
round trip through save then load should return exactly what was saved.
"""

from app.services.content_storage import load_activity_content, save_activity_content


def test_save_activity_content_returns_a_path(app) -> None:
    with app.app_context():
        path = save_activity_content("activity-1", {"body": "Some reading content."})

        assert path.endswith("activity-1.json")


def test_load_activity_content_round_trips_saved_content(app) -> None:
    with app.app_context():
        content = {"question": "Why?", "options": ["A", "B"]}
        path = save_activity_content("activity-2", content)

        loaded = load_activity_content(path)

        assert loaded == content
