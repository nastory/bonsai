"""Tests for study_tools_generation.py: standalone Flash Cards / Quiz Me generation."""

import pytest

from app.extensions import db as _db
from app.models import Activity, Course, FlashCardSet, Module, QuizSet
from app.services.content_storage import save_activity_content
from app.services.module_generation import ModuleNotFoundError
from app.services.study_tools_generation import (
    ModuleNotGeneratedError,
    generate_flash_cards,
    generate_quiz_set,
)


def _make_generated_module(module_id: str = "m1", course_id: str = "c1") -> Module:
    course = Course(
        id=course_id, title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
    )
    module = Module(
        id=module_id, course_id=course_id, position=0, title="GPU Basics",
        description="Foundational concepts.", estimated_timeline="1 week",
        status="in_progress", learning_outcomes=["Understand the basics"],
    )
    reading = Activity(id="a1", module_id=module_id, position=0, activity_type="reading", title="What Is a GPU?", status="available")
    reading.content_path = save_activity_content("a1", {"body": "A GPU is a specialized parallel processor."})
    quiz = Activity(id="a2", module_id=module_id, position=1, activity_type="quiz", title="Check", status="available")
    quiz.content_path = save_activity_content(
        "a2",
        {"questions": [{"question": "What is a GPU?", "options": ["A processor", "A monitor"], "correctAnswerIndex": 0, "explanation": "GPUs are processors."}]},
    )
    module.activities = [reading, quiz]
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_flash_cards_raises_for_unknown_module(app, db) -> None:
    with app.app_context():
        with pytest.raises(ModuleNotFoundError):
            generate_flash_cards("does-not-exist")


def test_generate_flash_cards_raises_when_module_has_no_content_yet(app, db) -> None:
    with app.app_context():
        course = Course(id="c1", title="T", description="d", prerequisites=[], estimated_timeline="1 week", thumbnail_url="x")
        module = Module(id="m1", course_id="c1", position=0, title="M", description="d", estimated_timeline="1 week", status="locked", learning_outcomes=[])
        course.modules = [module]
        _db.session.add(course)
        _db.session.commit()

        with pytest.raises(ModuleNotGeneratedError):
            generate_flash_cards("m1")


def test_generate_flash_cards_creates_and_persists_a_set(app, db) -> None:
    with app.app_context():
        module = _make_generated_module()

        result = generate_flash_cards(module.id)

        assert isinstance(result, FlashCardSet)
        assert result.module_id == "m1"
        assert len(result.cards) >= 1
        assert "question" in result.cards[0]
        assert "answer" in result.cards[0]


def test_generate_flash_cards_is_idempotent(app, db) -> None:
    with app.app_context():
        module = _make_generated_module()

        first = generate_flash_cards(module.id)
        second = generate_flash_cards(module.id)

        assert first.id == second.id


def test_generate_quiz_set_raises_for_unknown_module(app, db) -> None:
    with app.app_context():
        with pytest.raises(ModuleNotFoundError):
            generate_quiz_set("does-not-exist")


def test_generate_quiz_set_creates_and_persists_a_set(app, db) -> None:
    with app.app_context():
        module = _make_generated_module()

        result = generate_quiz_set(module.id)

        assert isinstance(result, QuizSet)
        assert result.module_id == "m1"
        assert len(result.questions) >= 1
        assert 0 <= result.questions[0]["correctAnswerIndex"] < len(result.questions[0]["options"])


def test_generate_quiz_set_is_idempotent(app, db) -> None:
    with app.app_context():
        module = _make_generated_module()

        first = generate_quiz_set(module.id)
        second = generate_quiz_set(module.id)

        assert first.id == second.id


def test_a_module_can_have_both_a_flash_card_set_and_a_quiz_set(app, db) -> None:
    with app.app_context():
        module = _make_generated_module()

        generate_flash_cards(module.id)
        generate_quiz_set(module.id)

        module = _db.session.get(Module, "m1")
        assert module.flash_card_set is not None
        assert module.quiz_set is not None
