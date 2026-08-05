"""Tests for in-course visual aids: splicing images into a finished reading activity's body.

Only runs for `reading` activities, only when UserSettings.visual_aids_enabled
and a Tavily key are both set - see module_generation.py's _add_visual_aids()/
_plan_visual_aids(), called from _generate_activities_content().

These test courses have no source materials, so _generate_activities_content()
also takes the web-search branch first (search-plan call before the activity
loop) - every canned-response list here starts with a search-plan response
(empty terms, so no actual web_search call) to account for that.
"""

from app.extensions import db as _db
from app.models import Course, Module, UserSettings
from app.services.module_generation import generate_module_activities


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _search_plan_response() -> _FakeResponse:
    return _FakeResponse('{"activities": [{"activityIndex": 0, "terms": []}]}')


def _make_module(activity_plan=None) -> Module:
    course = Course(
        id="c1",
        title="Bonsai Basics",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
        activity_plan=activity_plan
        or [{"type": "reading", "title": "Wiring", "plan": "Cover wiring techniques."}],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def _reading_body_response(body: str) -> str:
    return f'{{"type": "reading", "title": "Wiring", "estimatedMinutes": 10, "body": "{body}"}}'


def test_visual_aids_skipped_when_setting_is_off(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create().tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        # Search plan, activity body, digest - a visual-aid-planning call
        # would raise StopIteration if it happened.
        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse(_reading_body_response("Wire the branch carefully.")),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert result.activities[0].to_dict()["body"] == "Wire the branch carefully."


def test_visual_aids_skipped_without_a_tavily_key(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create().visual_aids_enabled = True
        _db.session.commit()
        module = _make_module()

        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse(_reading_body_response("Wire the branch carefully.")),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert result.activities[0].to_dict()["body"] == "Wire the branch carefully."


def test_visual_aids_splices_a_matched_aid_after_its_anchor_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.visual_aids_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse(_reading_body_response("Wire the branch carefully. Then let it set.")),
                _FakeResponse(
                    '{"aids": [{"query": "bonsai wiring", "caption": "Wiring a branch", '
                    '"anchorText": "Wire the branch carefully."}]}'
                ),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))
        monkeypatch.setattr(
            "app.services.module_generation.image_search",
            lambda query, api_key: [{"url": "https://example.com/wiring.jpg", "description": "A wired branch."}],
        )

        result = generate_module_activities(module.id)

        body = result.activities[0].to_dict()["body"]
        assert "![Wiring a branch](https://example.com/wiring.jpg)" in body
        assert body.index("Wire the branch carefully.") < body.index("![Wiring a branch]")


def test_visual_aids_silently_skips_an_aid_whose_anchor_text_is_not_found(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.visual_aids_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse(_reading_body_response("Wire the branch carefully.")),
                _FakeResponse(
                    '{"aids": [{"query": "bonsai wiring", "caption": "Wiring", '
                    '"anchorText": "This text is not in the body."}]}'
                ),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        def fail_if_called(*args, **kwargs):
            raise AssertionError("image_search should not be called for an unmatched anchor")

        monkeypatch.setattr("app.services.module_generation.image_search", fail_if_called)

        result = generate_module_activities(module.id)

        assert result.activities[0].to_dict()["body"] == "Wire the branch carefully."


def test_visual_aids_silently_skips_when_image_search_returns_nothing(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.visual_aids_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse(_reading_body_response("Wire the branch carefully.")),
                _FakeResponse(
                    '{"aids": [{"query": "bonsai wiring", "caption": "Wiring", '
                    '"anchorText": "Wire the branch carefully."}]}'
                ),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))
        monkeypatch.setattr("app.services.module_generation.image_search", lambda query, api_key: [])

        result = generate_module_activities(module.id)

        assert result.activities[0].to_dict()["body"] == "Wire the branch carefully."


def test_visual_aids_do_not_run_for_non_reading_activities(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.visual_aids_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module(activity_plan=[{"type": "discussion", "title": "Reflect", "plan": "Discuss wiring."}])

        def fail_if_called(*args, **kwargs):
            raise AssertionError("visual aids should not run for a non-reading activity")

        monkeypatch.setattr("app.services.module_generation.image_search", fail_if_called)
        canned = iter(
            [
                _search_plan_response(),
                _FakeResponse('{"type": "discussion", "title": "Reflect", "estimatedMinutes": 10, "prompt": "p"}'),
                _FakeResponse('{"digest": "Covered wiring."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        generate_module_activities(module.id)
