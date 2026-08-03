"""File-based storage for a source material's extracted text (see design.md's hybrid storage model).

Mirrors content_storage.py's save_activity_content/load_activity_content
pattern: one field, so plain text on disk rather than a JSON wrapper.
Instance-relative paths, not absolute, for the same reason content_storage.py
uses them (instance_path differs between a native run and a Docker container).
"""

from pathlib import Path

from flask import current_app

SOURCE_MATERIAL_SUBDIR = "source_material_text"


def save_source_material_text(source_material_id: str, text: str) -> str:
    """Write a source material's extracted text to disk.

    Args:
        source_material_id: The source material's id, used as the file's basename.
        text: The extracted text to persist.

    Returns:
        The path the text was written to, relative to instance_path, for
        storing on SourceMaterial.text_path.
    """
    relative_path = Path(SOURCE_MATERIAL_SUBDIR) / f"{source_material_id}.txt"
    absolute_path = Path(current_app.instance_path) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(text)
    return str(relative_path)


def load_source_material_text(text_path: str) -> str:
    """Read a source material's extracted text back from disk.

    Args:
        text_path: The path stored in SourceMaterial.text_path, relative to
            instance_path. An absolute path is also accepted.

    Returns:
        The extracted text previously saved.
    """
    path = Path(text_path)
    if not path.is_absolute():
        path = Path(current_app.instance_path) / path
    return path.read_text()
