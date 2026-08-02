"""Generates a module's learning activities.

Reuses the same schema-validation, mocking, and model-resolution patterns
established for course generation (see course_generation.py): canned
activities in LLM_TEST_MODE, the real complete() -> resolve_model_config()
path otherwise, and each activity's content-heavy fields are written to
disk via content_storage, per the hybrid storage model.
"""

from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import Activity, Module, UserSettings
from app.services.content_storage import save_activity_content
from app.services.llm import complete
from app.services.llm_schemas import CitationSchema, GeneratedActivitySchema, ModuleActivitiesSchema, validate_llm_json
from app.services.model_selection import resolve_model_config
from app.services.prompts import load_prompt
from app.services.retrieval_agent import run_agent


class ModuleNotFoundError(Exception):
    """Raised when a module-generation operation targets an unknown module id."""


def generate_module_activities(module_id: str) -> Module:
    """Generate and persist a module's learning activities, unless it already has some.

    Idempotent: a module that already has activities (the learner revisits
    it, or the trigger fires twice) is returned unchanged rather than
    generating duplicate content.

    Args:
        module_id: The module's id.

    Returns:
        The module, with its activities populated.

    Raises:
        ModuleNotFoundError: If no module matches module_id.
    """
    module = _get_module_or_raise(module_id)
    if module.activities:
        return module

    generated = _generate_activities_content(module)
    # All available, never locked: a module's activities are generated
    # together in this one call, so there's no such thing as "generated but
    # not reachable yet" for an activity the way there is for a module that
    # hasn't been generated at all.
    activities = [
        Activity(
            id=str(uuid4()),
            position=i,
            activity_type=a.type,
            title=a.title,
            status="available",
            estimated_minutes=a.estimatedMinutes,
        )
        for i, a in enumerate(generated.activities)
    ]

    for activity, a in zip(activities, generated.activities):
        content = a.model_dump(exclude={"type", "title", "estimatedMinutes"})
        activity.content_path = save_activity_content(activity.id, content)

    module.activities = activities
    db.session.commit()
    return module


def _get_module_or_raise(module_id: str) -> Module:
    module = db.session.get(Module, module_id)
    if module is None:
        raise ModuleNotFoundError(f"No module with id '{module_id}'")
    return module


def _generate_activities_content(module: Module) -> ModuleActivitiesSchema:
    if current_app.config.get("LLM_TEST_MODE"):
        return _mock_activities(module)

    prompt = load_prompt(
        "module_generation",
        course_title=module.course.title,
        course_description=module.course.description,
        module_title=module.title,
        module_description=module.description,
        learning_outcomes="\n".join(f"- {outcome}" for outcome in module.learning_outcomes),
    )
    messages = [{"role": "user", "content": prompt}]
    model_config = resolve_model_config()

    tavily_api_key = UserSettings.get_or_create().tavily_api_key
    if tavily_api_key:
        raw = run_agent(messages, model_config, tavily_api_key)
    else:
        raw = complete(messages=messages, **model_config)
    return validate_llm_json(raw, ModuleActivitiesSchema)


def _mock_activities(module: Module) -> ModuleActivitiesSchema:
    return ModuleActivitiesSchema(
        activities=[
            GeneratedActivitySchema(
                type="reading",
                title=f"[MOCK] Introduction to {module.title}",
                estimatedMinutes=15,
                body=f"[MOCK] A guided reading covering {module.title}.",
                citations=[CitationSchema(label="[MOCK] Example Source", url="https://example.com/mock-source")],
            ),
            GeneratedActivitySchema(
                type="discussion",
                title="[MOCK] Reflect and Discuss",
                estimatedMinutes=10,
                prompt="[MOCK] What stood out to you from this module so far?",
            ),
            GeneratedActivitySchema(
                type="assessment",
                title="[MOCK] Check Your Understanding",
                estimatedMinutes=10,
                question="[MOCK] Which of these best summarizes this module?",
                options=["[MOCK] Option A", "[MOCK] Option B"],
            ),
        ]
    )
