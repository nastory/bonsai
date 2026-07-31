"""Tests for the prompt-loading utility.

Prompts live as markdown files under app/prompts/, kept separate from code
so they're cleanly versionable on their own (see design.md). This tests the
loader against real prompt files, not fakes, since the files themselves are
checked-in content.
"""

import pytest

from app.services.prompts import load_prompt


def test_load_prompt_substitutes_variables() -> None:
    text = load_prompt("course_interview", topic="GPU programming", questions_asked=0, max_questions=10, history="")

    assert "GPU programming" in text
    assert "${" not in text  # no unfilled placeholders left behind


def test_load_prompt_raises_for_unknown_prompt() -> None:
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")
