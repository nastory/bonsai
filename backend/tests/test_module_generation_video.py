"""Tests for video embedding: adding one best-effort YouTube video activity per module.

Only attempted when UserSettings.video_embedding_enabled and a Tavily key are
both set, and the search-plan call actually suggested a query - see
module_generation.py's _maybe_build_video_spec()/_select_video(), called from
_generate_activities_content() right after the search plan is computed.

These test courses have no source materials, so _generate_activities_content()
also takes the web-search branch first (search-plan call before the activity
loop) - every canned-response list here starts with a search-plan response to
account for that.
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


def _search_plan_response(video_query: str = "", video_position: int = 0) -> _FakeResponse:
    return _FakeResponse(
        '{"activities": [{"activityIndex": 0, "terms": []}], '
        f'"videoSearchQuery": "{video_query}", "videoPosition": {video_position}}}'
    )


def _reading_body_response() -> _FakeResponse:
    return _FakeResponse('{"type": "reading", "title": "Wiring", "estimatedMinutes": 10, "body": "b"}')


def _digest_response() -> _FakeResponse:
    return _FakeResponse('{"digest": "Covered wiring."}')


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


def _one_candidate(url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ") -> list[dict]:
    return [{"title": "Bonsai Wiring 101", "url": url, "content": "A tutorial on wiring techniques."}]


def test_video_added_at_the_models_chosen_position(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.video_embedding_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        monkeypatch.setattr(
            "app.services.module_generation.video_search",
            lambda query, api_key: _one_candidate(),
        )
        canned = iter(
            [
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=1),
                _FakeResponse('{"selectedIndex": 0, "caption": "A great wiring tutorial."}'),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 2
        assert result.activities[0].activity_type == "reading"
        assert result.activities[0].position == 0
        video = result.activities[1]
        assert video.activity_type == "video"
        assert video.position == 1
        content = video.to_dict()
        assert content["videoId"] == "dQw4w9WgXcQ"
        assert content["videoUrl"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert content["caption"] == "A great wiring tutorial."


def test_video_skipped_when_setting_is_off(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create().tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("video_search should not be called when the toggle is off")

        monkeypatch.setattr("app.services.module_generation.video_search", fail_if_called)
        canned = iter(
            [
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=1),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 1
        assert result.activities[0].position == 0


def test_video_skipped_without_a_tavily_key(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        UserSettings.get_or_create().video_embedding_enabled = True
        _db.session.commit()
        module = _make_module()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("video_search should not be called without a Tavily key")

        monkeypatch.setattr("app.services.module_generation.video_search", fail_if_called)
        canned = iter(
            [
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=1),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 1


def test_video_skipped_when_model_suggests_no_query(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.video_embedding_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("video_search should not be called when videoSearchQuery is empty")

        monkeypatch.setattr("app.services.module_generation.video_search", fail_if_called)
        # Default video_query="" - the "most modules don't need one" case.
        canned = iter([_search_plan_response(), _reading_body_response(), _digest_response()])
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 1


def test_video_skipped_when_no_candidate_has_a_real_video_id(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.video_embedding_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        # A channel link, not a watch link - extract_youtube_video_id()
        # returns None for it, so it's filtered out before selection ever runs.
        monkeypatch.setattr(
            "app.services.module_generation.video_search",
            lambda query, api_key: [
                {"title": "Some Channel", "url": "https://www.youtube.com/channel/UC123", "content": "c"}
            ],
        )
        # Exactly 3 responses: if _select_video() ran anyway, the digest call
        # would consume this list out of order and fail to parse as
        # ModuleDigestSchema, failing loudly rather than silently passing.
        canned = iter(
            [
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=1),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 1


def test_video_skipped_when_model_declines_every_candidate(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.video_embedding_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        monkeypatch.setattr(
            "app.services.module_generation.video_search",
            lambda query, api_key: _one_candidate(),
        )
        canned = iter(
            [
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=1),
                _FakeResponse('{"selectedIndex": -1, "caption": ""}'),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 1


def test_video_position_is_clamped_to_a_valid_range(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.video_embedding_enabled = True
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        # Only one planned activity, so the only valid final positions are 0 and 1.
        module = _make_module()

        monkeypatch.setattr(
            "app.services.module_generation.video_search",
            lambda query, api_key: _one_candidate(),
        )
        canned = iter(
            [
                # A wildly out-of-range position a weak model might hallucinate.
                _search_plan_response(video_query="bonsai wiring tutorial", video_position=99),
                _FakeResponse('{"selectedIndex": 0, "caption": "A great wiring tutorial."}'),
                _reading_body_response(),
                _digest_response(),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert len(result.activities) == 2
        assert result.activities[1].activity_type == "video"
        assert result.activities[1].position == 1
