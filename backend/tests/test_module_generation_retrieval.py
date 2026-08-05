"""Tests for module generation's use of search planning + retrieval.

Search is now planned and executed deterministically before any activity
content is written (see module_retrieval.py), rather than left to a model
deciding for itself whether/what to search. When the learner has a Tavily
key configured, retrieved results should reach the activity-generation
prompt; without one, generation should proceed with no search results
(malformed-response handling for both stages is covered separately by
test_module_generation_llm_validation.py).
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


class _FakeEmbeddingItem(dict):
    """A dict subclass so item["embedding"] works, matching litellm's real response shape."""


class _FakeEmbeddingResponse:
    def __init__(self, num_vectors: int) -> None:
        self.data = [_FakeEmbeddingItem(embedding=[0.1, 0.2, 0.3]) for _ in range(num_vectors)]


def _fake_embedding(**kwargs):
    return _FakeEmbeddingResponse(len(kwargs["input"]))


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
        activity_plan=[{"type": "reading", "title": "Intro", "plan": "Cover the basics."}],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def _mock_completion(captured_prompts: list) -> callable:
    canned = [
        '{"activities": [{"activityIndex": 0, "terms": ["GPU basics"]}]}',
        '{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}',
        '{"digest": "Covered the basics."}',
    ]

    def fake_completion(**kwargs):
        captured_prompts.append(kwargs["messages"][-1]["content"])
        return _FakeResponse(canned[len(captured_prompts) - 1])

    return fake_completion


def test_generate_module_activities_passes_retrieved_results_to_activity_generation(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.tavily_api_key = "tvly-configured"
        settings.embedding_model = "test-embedding"
        _db.session.commit()
        module = _make_module()

        monkeypatch.setattr(
            "app.services.module_retrieval.web_search",
            lambda query, api_key, search_depth="basic": [
                {"title": "A GPU Primer", "url": "https://example.com/gpu-primer", "content": "GPUs are..."}
            ],
        )
        monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
        captured_prompts: list = []
        monkeypatch.setattr("app.services.llm.litellm.completion", _mock_completion(captured_prompts))

        generate_module_activities(module.id)

        # Fetched content is now chunked (via the source title) rather than
        # dumped raw, so the retrievable text is the title, not the raw URL.
        assert "A GPU Primer" in captured_prompts[1]


def test_generate_module_activities_attaches_a_real_url_citation_for_web_results(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.tavily_api_key = "tvly-configured"
        settings.embedding_model = "test-embedding"
        _db.session.commit()
        module = _make_module()

        monkeypatch.setattr(
            "app.services.module_retrieval.web_search",
            lambda query, api_key, search_depth="basic": [
                {"title": "A GPU Primer", "url": "https://example.com/gpu-primer", "content": "GPUs are..."}
            ],
        )
        monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
        captured_prompts: list = []
        monkeypatch.setattr("app.services.llm.litellm.completion", _mock_completion(captured_prompts))

        module_result = generate_module_activities(module.id)

        citations = module_result.activities[0].to_dict()["citations"]
        assert citations == [{"label": "A GPU Primer", "url": "https://example.com/gpu-primer"}]


def test_generate_module_activities_skips_retrieval_without_tavily_key(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("web_search should not be called without a Tavily key")

        monkeypatch.setattr("app.services.module_retrieval.web_search", fail_if_called)
        captured_prompts: list = []
        monkeypatch.setattr("app.services.llm.litellm.completion", _mock_completion(captured_prompts))

        generate_module_activities(module.id)

        assert "No material is available for this activity" in captured_prompts[1]


def test_generate_module_activities_uses_advanced_search_depth_when_deep_search_enabled(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        settings = UserSettings.get_or_create()
        settings.tavily_api_key = "tvly-configured"
        settings.deep_search_enabled = True
        _db.session.commit()
        module = _make_module()

        captured_search_depth: dict = {}

        def fake_web_search(query, api_key, search_depth="basic"):
            captured_search_depth["value"] = search_depth
            return []

        monkeypatch.setattr("app.services.module_retrieval.web_search", fake_web_search)
        captured_prompts: list = []
        monkeypatch.setattr("app.services.llm.litellm.completion", _mock_completion(captured_prompts))

        generate_module_activities(module.id)

        assert captured_search_depth["value"] == "advanced"
