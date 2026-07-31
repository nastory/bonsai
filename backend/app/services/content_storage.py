"""File-based storage for activity content (see design.md's hybrid storage model).

Structural fields (title, status, position, etc.) live in the database;
content-heavy generated fields (body, question, options, prompt) live in a
JSON file on disk under instance_path, referenced by Activity.content_path.
"""

import json
from pathlib import Path

from flask import current_app


def _content_dir() -> Path:
    directory = Path(current_app.instance_path) / "module_content"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_activity_content(activity_id: str, content: dict) -> str:
    """Write an activity's generated content to disk.

    Args:
        activity_id: The activity's id, used as the file's basename.
        content: The content fields to persist (body, question, options, prompt, etc.).

    Returns:
        The path the content was written to, for storing on Activity.content_path.
    """
    path = _content_dir() / f"{activity_id}.json"
    path.write_text(json.dumps(content))
    return str(path)


def load_activity_content(content_path: str) -> dict:
    """Read an activity's generated content back from disk.

    Args:
        content_path: The path stored in Activity.content_path.

    Returns:
        The content fields previously saved.
    """
    return json.loads(Path(content_path).read_text())
