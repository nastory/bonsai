"""File-based storage for activity content (see design.md's hybrid storage model).

Structural fields (title, status, position, etc.) live in the database;
content-heavy generated fields (body, question, options, prompt) live in a
JSON file on disk under instance_path, referenced by Activity.content_path.

content_path is stored relative to instance_path, not as an absolute path:
instance_path itself differs between a native run and a Docker container
(the same bind-mounted file is /app/instance in the container but an
absolute host path natively), so an absolute path baked into the database
would stop resolving the moment it's read from the other environment.
"""

import json
from pathlib import Path

from flask import current_app

CONTENT_SUBDIR = "module_content"


def save_activity_content(activity_id: str, content: dict) -> str:
    """Write an activity's generated content to disk.

    Args:
        activity_id: The activity's id, used as the file's basename.
        content: The content fields to persist (body, question, options, prompt, etc.).

    Returns:
        The path the content was written to, relative to instance_path, for
        storing on Activity.content_path.
    """
    relative_path = Path(CONTENT_SUBDIR) / f"{activity_id}.json"
    absolute_path = Path(current_app.instance_path) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(json.dumps(content))
    return str(relative_path)


def load_activity_content(content_path: str) -> dict:
    """Read an activity's generated content back from disk.

    Args:
        content_path: The path stored in Activity.content_path, relative to
            instance_path. An absolute path is also accepted, for content
            saved before content_path became instance-relative.

    Returns:
        The content fields previously saved.
    """
    path = Path(content_path)
    if not path.is_absolute():
        path = Path(current_app.instance_path) / path
    return json.loads(path.read_text())


def delete_activity_content(content_path: str) -> None:
    """Delete an activity's generated content from disk, e.g. when its course is deleted.

    Args:
        content_path: The path stored in Activity.content_path, relative to
            instance_path (or absolute, per load_activity_content's note).
            Missing files are ignored rather than erroring, since this is
            cleanup, not a load a caller depends on succeeding.
    """
    path = Path(content_path)
    if not path.is_absolute():
        path = Path(current_app.instance_path) / path
    path.unlink(missing_ok=True)
