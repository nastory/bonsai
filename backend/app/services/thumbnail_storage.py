"""File-based storage for a generated course thumbnail image (see design.md's hybrid storage model).

Mirrors source_material_storage.py's pattern, but for binary image bytes
rather than text, and resolve_thumbnail_image_path() returns a real path
(not the file's contents) since the serving route needs a path to hand to
Flask's send_file(), not bytes to read back into Python. Instance-relative
paths, not absolute, for the same reason source_material_storage.py uses
them (instance_path differs between a native run and a Docker container).
"""

from pathlib import Path

from flask import current_app

THUMBNAIL_SUBDIR = "thumbnails"


def save_thumbnail_image(course_id: str, image_bytes: bytes) -> str:
    """Write a course's generated thumbnail image to disk.

    Args:
        course_id: The course's id, used as the file's basename.
        image_bytes: The generated image's raw PNG bytes.

    Returns:
        The path the image was written to, relative to instance_path, for
        storing on Course.thumbnail_image_path.
    """
    relative_path = Path(THUMBNAIL_SUBDIR) / f"{course_id}.png"
    absolute_path = Path(current_app.instance_path) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)
    return str(relative_path)


def resolve_thumbnail_image_path(thumbnail_image_path: str) -> Path:
    """Resolve a stored thumbnail path to a real filesystem path.

    Args:
        thumbnail_image_path: The path stored in Course.thumbnail_image_path,
            relative to instance_path. An absolute path is also accepted.

    Returns:
        The absolute filesystem path to the image file.
    """
    path = Path(thumbnail_image_path)
    if not path.is_absolute():
        path = Path(current_app.instance_path) / path
    return path


def delete_thumbnail_image(thumbnail_image_path: str) -> None:
    """Delete a course's generated thumbnail image from disk, e.g. when its course is deleted.

    Args:
        thumbnail_image_path: The path stored in Course.thumbnail_image_path,
            relative to instance_path (or absolute, per resolve_thumbnail_image_path's
            note). Missing files are ignored rather than erroring, since this
            is cleanup, not a load a caller depends on succeeding.
    """
    resolve_thumbnail_image_path(thumbnail_image_path).unlink(missing_ok=True)
