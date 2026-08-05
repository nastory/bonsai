"""Tests for file-based thumbnail image storage.

Mirrors test_source_material_storage.py: a round trip through save then
resolve should point at exactly the bytes that were saved, with an
instance-relative (not absolute) path.
"""

from pathlib import Path

from app.services.thumbnail_storage import (
    delete_thumbnail_image,
    resolve_thumbnail_image_path,
    save_thumbnail_image,
)


def test_save_thumbnail_image_returns_a_path_relative_to_instance_path(app) -> None:
    with app.app_context():
        path = save_thumbnail_image("course-1", b"fake-png-bytes")

        assert path.endswith("course-1.png")
        assert not Path(path).is_absolute()


def test_resolve_thumbnail_image_path_round_trips_saved_bytes(app) -> None:
    with app.app_context():
        image_bytes = b"a fake png's bytes"
        path = save_thumbnail_image("course-2", image_bytes)

        resolved = resolve_thumbnail_image_path(path)

        assert resolved.read_bytes() == image_bytes


def test_resolve_thumbnail_image_path_accepts_an_absolute_path(app, tmp_path) -> None:
    image_file = tmp_path / "legacy-thumbnail.png"
    image_file.write_bytes(b"legacy bytes")

    with app.app_context():
        resolved = resolve_thumbnail_image_path(str(image_file))

    assert resolved.read_bytes() == b"legacy bytes"


def test_delete_thumbnail_image_removes_the_file(app) -> None:
    with app.app_context():
        path = save_thumbnail_image("course-3", b"bytes to delete")
        absolute_path = Path(app.instance_path) / path
        assert absolute_path.exists()

        delete_thumbnail_image(path)

        assert not absolute_path.exists()


def test_delete_thumbnail_image_is_a_no_op_for_a_missing_file(app) -> None:
    with app.app_context():
        delete_thumbnail_image("thumbnails/does-not-exist.png")
