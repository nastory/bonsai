"""Tests for module generation's use of the retrieval agent.

When the learner has a Tavily API key configured, module generation should
route through the search/fetch/evaluate agent loop instead of a single
plain completion. Without one, it should fall back to plain generation
(covered by test_module_generation_llm_validation.py, which never sets a key).
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


def _make_module() -> Module:
    course = Course(
        id="c1",
        title="GPU Programming",
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
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_generate_module_activities_uses_retrieval_agent_when_tavily_key_configured(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.tavily_api_key = "tvly-configured"
        _db.session.commit()
        module = _make_module()

        captured: dict = {}

        def fake_run_agent(messages, model_config, tavily_api_key):
            captured["messages"] = messages
            captured["model_config"] = model_config
            captured["tavily_api_key"] = tavily_api_key
            return (
                '{"activities": [{"type": "reading", "title": "T", "estimatedMinutes": 10, "body": "b", '
                '"citations": [{"label": "A Source", "url": "https://example.com"}]}]}'
            )

        monkeypatch.setattr("app.services.module_generation.run_agent", fake_run_agent)
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: (_ for _ in ()).throw(AssertionError("plain completion should not be called")),
        )

        result = generate_module_activities(module.id)

        assert captured["tavily_api_key"] == "tvly-configured"
        assert result.activities[0].to_dict()["citations"][0]["label"] == "A Source"


def test_generate_module_activities_skips_retrieval_agent_without_tavily_key(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("run_agent should not be called without a Tavily key")

        monkeypatch.setattr("app.services.module_generation.run_agent", fail_if_called)
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse(
                '{"activities": [{"type": "reading", "title": "T", "estimatedMinutes": 10}]}'
            ),
        )

        result = generate_module_activities(module.id)

        assert result.activities[0].title == "T"
