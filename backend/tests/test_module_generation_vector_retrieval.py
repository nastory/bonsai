"""Tests for module generation's normal document-grounded path: per-activity vector retrieval.

When a course has a real vector index (Course.vector_index_path set - see
vector_store.py), module generation retrieves each activity's most relevant
chunks directly instead of dumping the whole document into every module's
seed prompt, and never calls plan_activity_searches()/retrieve_for_module()
(the web-search path) either. For the legacy fallback (source materials
without a vector index), see test_module_generation_source_materials.py.
"""

from app.extensions import db as _db
from app.models import Course, Module, SourceMaterial, UserSettings
from app.services.document_chunking import Chunk
from app.services.module_generation import generate_module_activities
from app.services.source_material_storage import save_source_material_text
from app.services.vector_store import build_or_update_index


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


def _make_module_with_vector_index(monkeypatch) -> Module:
    monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
    UserSettings.get_or_create().embedding_model = "test-embedding"
    _db.session.commit()

    course = Course(
        id="c-vec-1",
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    text_path = save_source_material_text("src-vec-1", "GPU memory coalescing improves throughput significantly.")
    course.source_materials = [SourceMaterial(id="src-vec-1", file_name="paper.pdf", text_path=text_path)]

    chunks = [
        Chunk(text="GPU memory coalescing improves throughput significantly.", source="paper.pdf", page=1),
        Chunk(text="Warp scheduling determines how threads execute in parallel.", source="paper.pdf", page=2),
    ]
    course.vector_index_path = build_or_update_index(course, chunks, {"model": "test-embedding"})

    module = Module(
        id="m-vec-1",
        course_id="c-vec-1",
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


def _make_module_with_two_document_vector_index(monkeypatch) -> Module:
    monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
    UserSettings.get_or_create().embedding_model = "test-embedding"
    _db.session.commit()

    course = Course(
        id="c-vec-multi",
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    path1 = save_source_material_text("src-vec-multi-1", "GPU memory coalescing improves throughput.")
    path2 = save_source_material_text("src-vec-multi-2", "Warp scheduling determines thread execution.")
    course.source_materials = [
        SourceMaterial(id="src-vec-multi-1", file_name="memory.pdf", text_path=path1),
        SourceMaterial(id="src-vec-multi-2", file_name="scheduling.pdf", text_path=path2),
    ]

    chunks = [
        Chunk(text="GPU memory coalescing improves throughput.", source="memory.pdf", page=1),
        Chunk(text="Uncoalesced access patterns hurt bandwidth.", source="memory.pdf", page=2),
        Chunk(text="Warp scheduling determines thread execution.", source="scheduling.pdf", page=1),
        Chunk(text="Occupancy affects how warps are scheduled.", source="scheduling.pdf", page=2),
    ]
    course.vector_index_path = build_or_update_index(course, chunks, {"model": "test-embedding"})

    module = Module(
        id="m-vec-multi",
        course_id="c-vec-multi",
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


def test_vector_grounded_citations_correctly_attribute_multiple_documents(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_two_document_vector_index(monkeypatch)
        canned = iter(
            [
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        labels = {c["label"] for c in result.activities[0].to_dict()["citations"]}
        # MAX_CHUNKS_PER_ACTIVITY=4 and the index has exactly 4 chunks total
        # (2 per document), so every chunk from both documents is retrieved -
        # citations should span both files, not just whichever came first.
        assert any(label.startswith("memory.pdf") for label in labels)
        assert any(label.startswith("scheduling.pdf") for label in labels)


def test_vector_grounded_module_never_calls_search_planning_or_web_search(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_vector_index(monkeypatch)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("search should not be called when the course has a vector index")

        monkeypatch.setattr("app.services.module_generation.plan_activity_searches", fail_if_called)
        monkeypatch.setattr("app.services.module_retrieval.web_search", fail_if_called)

        canned = iter(
            [
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert result.activities[0].title == "Intro"


def test_vector_grounded_module_seed_prompt_has_no_whole_document_block(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_vector_index(monkeypatch)

        captured_calls: list[list[dict]] = []
        canned = [
            '{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}',
            '{"digest": "Covered the basics."}',
        ]

        def fake_completion(**kwargs):
            captured_calls.append(kwargs["messages"])
            return _FakeResponse(canned[len(captured_calls) - 1])

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_module_activities(module.id)

        # First call is activity generation: [system, user(seed data message), user(activity 1 turn)].
        seed_data_message = captured_calls[0][1]["content"]
        activity_turn_message = captured_calls[0][2]["content"]
        assert "Source materials the learner has provided" not in seed_data_message
        assert "GPU memory coalescing improves throughput significantly." in activity_turn_message
        assert "paper.pdf, p. 1" in activity_turn_message


def test_vector_grounded_reading_activity_gets_deterministic_citations(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_vector_index(monkeypatch)
        canned = iter(
            [
                # Model omits citations entirely - deterministic attachment
                # should still populate them from the retrieved chunks.
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        citations = result.activities[0].to_dict().get("citations")
        assert citations
        labels = {c["label"] for c in citations}
        assert "paper.pdf, p. 1" in labels
        assert all(c["url"] is None for c in citations)


def test_vector_grounded_module_ignores_model_authored_citations(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_vector_index(monkeypatch)
        canned = iter(
            [
                _FakeResponse(
                    '{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b", '
                    '"citations": [{"label": "hallucinated", "url": "https://example.com/fake"}]}'
                ),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        labels = {c["label"] for c in result.activities[0].to_dict()["citations"]}
        assert "hallucinated" not in labels


def test_vector_grounded_module_generates_successfully_under_llm_test_mode(client, db) -> None:
    course = Course(
        id="c-vec-2", title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
    )
    text_path = save_source_material_text("src-vec-2", "GPU memory coalescing text.")
    course.source_materials = [SourceMaterial(id="src-vec-2", file_name="paper.txt", text_path=text_path)]
    course.vector_index_path = "vector_indexes/c-vec-2.faiss"
    module = Module(
        id="m-vec-2", course_id="c-vec-2", position=0, title="Getting Started", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
        activity_plan=[{"type": "reading", "title": "Intro", "plan": "p"}],
    )
    course.modules = [module]
    db.session.add(course)
    db.session.commit()

    response = client.post(f"/api/modules/{module.id}/generate-activities")

    assert response.status_code == 200
    generated_module = next(m for m in response.get_json()["modules"] if m["id"] == "m-vec-2")
    assert len(generated_module["activities"]) >= 1
