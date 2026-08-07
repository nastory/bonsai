"""Generates and persists standalone study tools (flash cards, a Quiz Me quiz) from a module's real content.

Both features share the exact same grounding step - a full-fidelity
concatenation of everything the module's activities actually say - and only
differ in prompt/schema, so they live in one file rather than two. Generated
once and reused forever: same "generate once" precedent module activities
themselves already follow (see module_generation.py) - there is no route to
replace a saved set once created.
"""

from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import FlashCardSet, Module, QuizSet
from app.services.llm import complete
from app.services.llm_schemas import (
    FlashCardSchema,
    GeneratedFlashCardSetSchema,
    GeneratedQuizSetSchema,
    QuizQuestionSchema,
    validate_llm_json,
)
from app.services.model_selection import resolve_model_config
from app.services.module_generation import ModuleNotFoundError
from app.services.prompts import load_prompt


class ModuleNotGeneratedError(Exception):
    """Raised when flash cards/a quiz are requested for a module with no generated activities yet."""


def _get_module_or_raise(module_id: str) -> Module:
    module = db.session.get(Module, module_id)
    if module is None:
        raise ModuleNotFoundError(f"No module with id '{module_id}'")
    return module


def _render_module_full_content(module: Module) -> str:
    """Every activity's real generated content for this module, verbatim.

    Unlike module_generation.py's _format_generated_activities() (which
    truncates each activity to ~300 chars for a lightweight cross-module
    digest) or a module's learning-history digest (a single condensed
    paragraph, explicitly too lossy for this - see module_digest.md's own
    "without repeating full content" instruction), flash cards/quiz need
    real detail to write checkable question/answer pairs from. Reads each
    activity's full to_dict()-merged content untouched.

    Args:
        module: The module, with its activities already generated.

    Returns:
        The module's content, one activity per paragraph. Video activities
        (caption-only, no real textual content) are skipped.
    """
    parts = []
    for activity in module.activities:
        content = activity.to_dict()
        if content.get("body"):
            parts.append(f"[{activity.activity_type}] {activity.title}\n{content['body']}")
        elif content.get("prompt"):
            parts.append(f"[{activity.activity_type}] {activity.title}\n{content['prompt']}")
        elif content.get("questions"):
            questions_text = "\n".join(
                f"Q: {q['question']}\nA: {q['options'][q['correctAnswerIndex']]} ({q['explanation']})"
                for q in content["questions"]
            )
            parts.append(f"[{activity.activity_type}] {activity.title}\n{questions_text}")
    return "\n\n".join(parts)


def _module_data_message(module: Module) -> str:
    return f"Module: {module.title}\n{module.description}\n\n{_render_module_full_content(module)}"


def generate_flash_cards(module_id: str) -> FlashCardSet:
    """Generate and persist a module's flash cards, unless it already has some.

    Idempotent: a module that already has a saved flash card set returns it
    unchanged - flash cards are never regenerated once created, same
    precedent as module activities themselves.

    Args:
        module_id: The module's id.

    Returns:
        The module's flash card set (freshly generated, or the existing one).

    Raises:
        ModuleNotFoundError: If no module matches module_id.
        ModuleNotGeneratedError: If the module has no generated activities yet.
        LLMOutputValidationError: If the model's response doesn't match GeneratedFlashCardSetSchema.
    """
    module = _get_module_or_raise(module_id)
    if module.flash_card_set is not None:
        return module.flash_card_set
    if not module.activities:
        raise ModuleNotGeneratedError(f"Module '{module_id}' has no generated content yet")

    generated = _generate_flash_card_content(module)
    flash_card_set = FlashCardSet(id=str(uuid4()), module_id=module.id, cards=[c.model_dump() for c in generated.cards])
    db.session.add(flash_card_set)
    db.session.commit()
    return flash_card_set


def _generate_flash_card_content(module: Module) -> GeneratedFlashCardSetSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return GeneratedFlashCardSetSchema(
            cards=[
                FlashCardSchema(question=f"[MOCK] Question {n} about {module.title}?", answer=f"[MOCK] Answer {n}.")
                for n in range(1, 7)
            ]
        )

    messages = [
        {"role": "system", "content": load_prompt("flash_card_generation")},
        {"role": "user", "content": _module_data_message(module)},
    ]
    raw = complete(
        messages=messages,
        schema=GeneratedFlashCardSetSchema,
        course_id=module.course_id,
        module_id=module.id,
        call_type="flash_cards",
        **resolve_model_config(),
    )
    return validate_llm_json(raw, GeneratedFlashCardSetSchema)


def generate_quiz_set(module_id: str) -> QuizSet:
    """Generate and persist a module's standalone Quiz Me quiz, unless it already has one.

    Idempotent, same precedent as generate_flash_cards()/module activities.

    Args:
        module_id: The module's id.

    Returns:
        The module's quiz set (freshly generated, or the existing one).

    Raises:
        ModuleNotFoundError: If no module matches module_id.
        ModuleNotGeneratedError: If the module has no generated activities yet.
        LLMOutputValidationError: If the model's response doesn't match GeneratedQuizSetSchema.
    """
    module = _get_module_or_raise(module_id)
    if module.quiz_set is not None:
        return module.quiz_set
    if not module.activities:
        raise ModuleNotGeneratedError(f"Module '{module_id}' has no generated content yet")

    generated = _generate_quiz_set_content(module)
    quiz_set = QuizSet(id=str(uuid4()), module_id=module.id, questions=[q.model_dump() for q in generated.questions])
    db.session.add(quiz_set)
    db.session.commit()
    return quiz_set


def _generate_quiz_set_content(module: Module) -> GeneratedQuizSetSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return GeneratedQuizSetSchema(
            questions=[
                QuizQuestionSchema(
                    question=f"[MOCK] Question {n} about {module.title}?",
                    options=["[MOCK] Option A", "[MOCK] Option B"],
                    correctAnswerIndex=0,
                    explanation="[MOCK] Explanation.",
                )
                for n in range(1, 5)
            ]
        )

    messages = [
        {"role": "system", "content": load_prompt("quiz_me_generation")},
        {"role": "user", "content": _module_data_message(module)},
    ]
    raw = complete(
        messages=messages,
        schema=GeneratedQuizSetSchema,
        course_id=module.course_id,
        module_id=module.id,
        call_type="quiz_me",
        **resolve_model_config(),
    )
    return validate_llm_json(raw, GeneratedQuizSetSchema)
