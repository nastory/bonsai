"""Tests for ama.py: the Ask Me Anything retrieval/answer pipeline.

Runs under LLM_TEST_MODE, so embedding is the deterministic-but-not-
semantically-meaningful mock from embedding.py (see test_vector_store.py) -
these check the pipeline's branching (no candidates, no embedding model,
off-topic decline, real retrieval + citation attribution), not real
retrieval relevance.
"""

from app.extensions import db as _db
from app.models import Course, UserSettings
from app.services.ama import DECLINE_NO_COURSES, DECLINE_OFF_TOPIC, _merge_term_results, answer_ama_question
from app.services.document_chunking import Chunk
from app.services.vector_store import build_or_update_index

_CONFIG = {"model": "mock-embedding-model"}


def _make_indexed_course(course_id: str, title: str, *texts: str) -> Course:
    course = Course(
        id=course_id, title=title, description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
    )
    chunks = [Chunk(text=t, source="notes.pdf", page=i + 1) for i, t in enumerate(texts)]
    course.vector_index_path = build_or_update_index(course, chunks, _CONFIG)
    _db.session.add(course)
    _db.session.commit()
    return course


def test_answer_ama_question_declines_when_no_course_has_an_index(app, db) -> None:
    with app.app_context():
        Course(
            id="c1", title="T", description="d", prerequisites=[],
            estimated_timeline="1 week", thumbnail_url="x",
        )
        result = answer_ama_question("what is a GPU?", [])

    assert result.reply == DECLINE_NO_COURSES
    assert result.course_ids == []
    assert result.citations == []


def test_answer_ama_question_returns_a_grounded_reply_with_citations(app, db) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")

        result = answer_ama_question("what is a GPU?", [])

    assert result.reply.startswith("[MOCK]")
    assert result.course_ids == ["c1"]
    assert len(result.citations) >= 1
    assert result.citations[0].label.startswith("GPU Programming: notes.pdf")


def test_answer_ama_question_declines_when_selected_course_yields_no_chunks(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        monkeypatch.setattr("app.services.ama.query_vector_store", lambda *a, **k: {0: []})

        result = answer_ama_question("what is a GPU?", [])

    assert result.reply == DECLINE_OFF_TOPIC
    assert result.course_ids == []


def test_answer_ama_question_declines_when_classifier_picks_no_course(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        monkeypatch.setattr("app.services.ama._select_courses", lambda *a, **k: [])

        result = answer_ama_question("what's the capital of France?", [])

    assert result.reply == DECLINE_OFF_TOPIC


def test_answer_ama_question_ignores_hallucinated_course_ids(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        monkeypatch.setattr("app.services.ama._select_courses", lambda *a, **k: ["does-not-exist"])

        result = answer_ama_question("what is a GPU?", [])

    assert result.reply == DECLINE_OFF_TOPIC


def test_answer_ama_question_merges_chunks_from_up_to_three_selected_courses(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        _make_indexed_course("c2", "Databases", "A B-tree index speeds up lookups.")
        monkeypatch.setattr("app.services.ama._select_courses", lambda *a, **k: ["c1", "c2"])

        result = answer_ama_question("compare GPUs and databases", [])

    assert sorted(result.course_ids) == ["c1", "c2"]
    labels = [c.label for c in result.citations]
    assert any(label.startswith("GPU Programming:") for label in labels)
    assert any(label.startswith("Databases:") for label in labels)


def test_answer_ama_question_queries_the_vector_store_with_optimized_terms_not_the_raw_message(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        monkeypatch.setattr("app.services.ama._optimize_search_terms", lambda *a, **k: ["gpu architecture", "parallel processor"])
        captured = {}

        def _fake_query(course, query_texts, config, top_k):
            captured["query_texts"] = query_texts
            return {i: [] for i in range(len(query_texts))}

        monkeypatch.setattr("app.services.ama.query_vector_store", _fake_query)

        answer_ama_question("tell me more about that", [])

    assert captured["query_texts"] == ["gpu architecture", "parallel processor"]


def test_answer_ama_question_classifies_using_optimized_terms(app, db, monkeypatch) -> None:
    with app.app_context():
        _make_indexed_course("c1", "GPU Programming", "A GPU is a specialized parallel processor.")
        monkeypatch.setattr("app.services.ama._optimize_search_terms", lambda *a, **k: ["gpu memory coalescing"])
        captured = {}

        def _fake_select(search_terms, history, candidates):
            captured["search_terms"] = search_terms
            return [candidates[0].id]

        monkeypatch.setattr("app.services.ama._select_courses", _fake_select)

        answer_ama_question("what about that thing we discussed?", [])

    assert captured["search_terms"] == ["gpu memory coalescing"]


def test_merge_term_results_interleaves_and_dedupes_across_terms() -> None:
    a1 = Chunk(text="a1", source="s.pdf", page=1)
    a2 = Chunk(text="a2", source="s.pdf", page=2)
    b1 = Chunk(text="b1", source="s.pdf", page=3)
    shared = Chunk(text="shared", source="s.pdf", page=4)

    merged = _merge_term_results([[a1, shared, a2], [b1, shared]])

    # Round-robin: term 1's first pick, then term 2's first pick, before
    # either term's second pick - and the chunk both terms surfaced only
    # appears once.
    assert merged == [a1, b1, shared, a2]


def test_merge_term_results_handles_a_single_term_unchanged() -> None:
    a1 = Chunk(text="a1", source="s.pdf", page=1)
    a2 = Chunk(text="a2", source="s.pdf", page=2)

    assert _merge_term_results([[a1, a2]]) == [a1, a2]


def test_answer_ama_question_declines_when_no_embedding_model_and_not_test_mode(monkeypatch) -> None:
    from app import create_app

    real_app = create_app(test=False, in_memory_db=True)
    with real_app.app_context():
        _db.create_all()
        UserSettings.get_or_create()  # embedding_model left unset
        _make_indexed_course_no_embed = Course(
            id="c1", title="T", description="d", prerequisites=[],
            estimated_timeline="1 week", thumbnail_url="x", vector_index_path="vector_indexes/c1.faiss",
        )
        _db.session.add(_make_indexed_course_no_embed)
        _db.session.commit()

        result = answer_ama_question("what is a GPU?", [])

        _db.session.remove()
        _db.drop_all()

    assert result.reply == DECLINE_NO_COURSES
