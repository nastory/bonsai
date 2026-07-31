"""Tests for module content generation.

Reuses the mock/real branching pattern from course_generation.py: mocked
canned activities in LLM_TEST_MODE, the real complete()/resolve_model_config()
path otherwise. Every generated activity's content-heavy fields are written
to disk via content_storage, matching the hybrid storage model.
"""

import pytest

from app.extensions import db as _db
from app.models import Course, Module
from app.services.module_generation import ModuleNotFoundError, generate_module_activities


def _make_module(course_id: str = "c1") -> Module:
    course = Course(
        id=course_id,
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    module = Module(
        id="m1",
        course_id=course_id,
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_module_activities_raises_for_unknown_module(db) -> None:
    with pytest.raises(ModuleNotFoundError):
        generate_module_activities("does-not-exist")


def test_generate_module_activities_populates_activities(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    assert len(result.activities) >= 1
    assert result.activities[0].status == "available"
    assert all(a.status == "locked" for a in result.activities[1:])


def test_generate_module_activities_writes_content_path_for_each_activity(db) -> None:
    module = _make_module()

    result = generate_module_activities(module.id)

    for activity in result.activities:
        assert activity.content_path is not None
        data = activity.to_dict()
        assert "id" in data


def test_generate_module_activities_is_idempotent(db) -> None:
    module = _make_module()

    first = generate_module_activities(module.id)
    first_ids = [a.id for a in first.activities]

    second = generate_module_activities(module.id)

    assert [a.id for a in second.activities] == first_ids
