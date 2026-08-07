"""Tests for reset_all_data() (see app/services/course_generation.py).

A full factory reset: every course and its on-disk content/vector index/
thumbnail, every LLMUsageLog row, and the single UserSettings row
(including API keys) all get wiped, with a fresh default UserSettings row
left in place afterward.
"""

import pytest

from app.extensions import db
from app.models import Activity, Course, LLMUsageLog, Module, UserSettings
from app.services.content_storage import load_activity_content, save_activity_content
from app.services.course_generation import reset_all_data


def _make_course_with_content(course_id: str = "c1") -> None:
    course = Course(
        id=course_id, title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="4 weeks", thumbnail_url="x", stage="active",
    )
    module = Module(
        id="m1", course_id=course_id, position=0, title="Basics", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    content_path = save_activity_content("a1", {"body": "Some reading content."})
    activity = Activity(
        id="a1", module_id="m1", position=0, activity_type="reading", title="Intro",
        status="completed", content_path=content_path,
    )
    module.activities = [activity]
    course.modules = [module]
    db.session.add(course)
    db.session.commit()


def test_reset_all_data_deletes_every_course_and_its_content(app, db) -> None:
    with app.app_context():
        _make_course_with_content()
        content_path = db.session.get(Activity, "a1").content_path

        reset_all_data()

        assert db.session.get(Course, "c1") is None
        with pytest.raises(FileNotFoundError):
            load_activity_content(content_path)


def test_reset_all_data_deletes_usage_logs(app, db) -> None:
    with app.app_context():
        db.session.add(LLMUsageLog(call_type="course_outline", model="m", prompt_tokens=1, completion_tokens=1, total_tokens=2))
        db.session.commit()

        reset_all_data()

        assert db.session.execute(db.select(LLMUsageLog)).first() is None


def test_reset_all_data_replaces_settings_with_fresh_defaults(app, db) -> None:
    with app.app_context():
        settings = UserSettings.get_or_create()
        settings.name = "Alex"
        settings.model_provider_api_key = "secret-key"
        settings.onboarding_completed = True
        db.session.commit()

        reset_all_data()

        fresh = UserSettings.get_or_create()
        assert fresh.name == "Learner"
        assert fresh.model_provider_api_key is None
        assert fresh.onboarding_completed is False


def test_reset_all_data_leaves_no_courses_when_none_existed(app, db) -> None:
    with app.app_context():
        reset_all_data()

        assert db.session.execute(db.select(Course)).first() is None
