"""Tests for POST /api/ama/messages."""

from app.extensions import db as _db
from app.models import Course
from app.services.document_chunking import Chunk
from app.services.vector_store import build_or_update_index

_CONFIG = {"model": "mock-embedding-model"}


def _seed_indexed_course() -> None:
    course = Course(
        id="c1", title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
    )
    chunks = [Chunk(text="A GPU is a specialized parallel processor.", source="notes.pdf", page=1)]
    course.vector_index_path = build_or_update_index(course, chunks, _CONFIG)
    _db.session.add(course)
    _db.session.commit()


def test_post_ama_message_returns_a_reply_with_citations(client, db) -> None:
    _seed_indexed_course()

    response = client.post("/api/ama/messages", json={"message": "what is a GPU?", "history": []})

    assert response.status_code == 200
    body = response.get_json()
    assert body["reply"].startswith("[MOCK]")
    assert body["courseIds"] == ["c1"]
    assert len(body["citations"]) >= 1
    assert "label" in body["citations"][0]


def test_post_ama_message_requires_a_nonempty_message(client, db) -> None:
    response = client.post("/api/ama/messages", json={"message": "  ", "history": []})

    assert response.status_code == 400


def test_post_ama_message_requires_message_field(client, db) -> None:
    response = client.post("/api/ama/messages", json={"history": []})

    assert response.status_code == 400


def test_post_ama_message_declines_with_no_indexed_courses(client, db) -> None:
    response = client.post("/api/ama/messages", json={"message": "what is a GPU?", "history": []})

    assert response.status_code == 200
    body = response.get_json()
    assert body["courseIds"] == []
    assert body["citations"] == []


def test_post_ama_message_accepts_prior_history(client, db) -> None:
    _seed_indexed_course()

    response = client.post(
        "/api/ama/messages",
        json={"message": "tell me more", "history": [{"role": "user", "content": "what is a GPU?"}, {"role": "assistant", "content": "[MOCK] answer"}]},
    )

    assert response.status_code == 200
