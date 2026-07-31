"""Loader for prompt templates stored as markdown files under app/prompts/.

Prompts are kept as plain text files, separate from application code, so
they're cleanly versionable on their own: a prompt-wording change shows up
as a diff to a .md file, not tangled into a code diff.
"""

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, **variables: object) -> str:
    """Load a prompt template and substitute its variables.

    Args:
        name: The prompt's filename without the .md extension.
        **variables: Values for the template's ``${variable}`` placeholders.

    Returns:
        The rendered prompt text.

    Raises:
        FileNotFoundError: If no prompt file matches ``name``.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"No prompt template named '{name}' in {PROMPTS_DIR}")

    template = Template(path.read_text())
    return template.substitute(**variables)
