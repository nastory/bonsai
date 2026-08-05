"""Tests for the per-course FAISS vector store.

Runs against LLM_TEST_MODE's deterministic-but-not-semantically-meaningful
mock embeddings (see test_embedding.py), so these only check the storage/
retrieval plumbing (round-tripping, incremental addition, path handling,
deletion) - not real retrieval relevance, which needs a real embedding
model to mean anything.

Like test_source_material_storage.py, this writes to the real (test-mode)
instance_path via the `app` fixture rather than a fully isolated tmp dir,
using distinctive course ids so it doesn't collide with real dev data.
"""

from pathlib import Path

from app.models import Course
from app.services.document_chunking import Chunk
from app.services.vector_store import build_or_update_index, delete_vector_index, query

_CONFIG = {"model": "text-embedding-3-small"}


def _chunks(*texts: str, source: str = "paper.pdf") -> list[Chunk]:
    return [Chunk(text=t, source=source, page=i + 1) for i, t in enumerate(texts)]


def test_query_returns_empty_lists_when_course_has_no_index(app) -> None:
    course = Course(id="vec-test-no-index")

    with app.app_context():
        result = query(course, ["what is this about?"], _CONFIG, top_k=3)

    assert result == {0: []}


def test_build_or_update_index_returns_a_path_relative_to_instance_path(app) -> None:
    course = Course(id="vec-test-1")

    with app.app_context():
        path = build_or_update_index(course, _chunks("GPU memory coalescing."), _CONFIG)

    assert not Path(path).is_absolute()
    assert path.endswith("vec-test-1.faiss")


def test_query_round_trips_added_chunks(app) -> None:
    course = Course(id="vec-test-2")

    with app.app_context():
        path = build_or_update_index(
            course, _chunks("GPU memory coalescing.", "Warp scheduling basics.", "Shared memory banks."), _CONFIG
        )
        course.vector_index_path = path

        result = query(course, ["memory access patterns"], _CONFIG, top_k=2)

    assert len(result) == 1
    assert len(result[0]) == 2
    for chunk in result[0]:
        assert chunk.source == "paper.pdf"
        assert chunk.page is not None


def test_query_round_trips_a_web_chunks_url_and_no_page(app) -> None:
    course = Course(id="vec-test-web-1")
    web_chunk = [Chunk(text="GPUs execute threads in warps.", source="A GPU Primer", url="https://example.com/gpu")]

    with app.app_context():
        path = build_or_update_index(course, web_chunk, _CONFIG)
        course.vector_index_path = path

        result = query(course, ["how do GPUs work"], _CONFIG, top_k=1)

    chunk = result[0][0]
    assert chunk.source == "A GPU Primer"
    assert chunk.url == "https://example.com/gpu"
    assert chunk.page is None


def test_query_caps_results_at_the_total_number_of_stored_chunks(app) -> None:
    course = Course(id="vec-test-3")

    with app.app_context():
        path = build_or_update_index(course, _chunks("Only one chunk here."), _CONFIG)
        course.vector_index_path = path

        result = query(course, ["anything"], _CONFIG, top_k=10)

    assert len(result[0]) == 1


def test_query_handles_multiple_queries_independently(app) -> None:
    course = Course(id="vec-test-4")

    with app.app_context():
        path = build_or_update_index(course, _chunks("First chunk.", "Second chunk.", "Third chunk."), _CONFIG)
        course.vector_index_path = path

        result = query(course, ["query one", "query two"], _CONFIG, top_k=1)

    assert set(result.keys()) == {0, 1}
    assert len(result[0]) == 1
    assert len(result[1]) == 1


def test_build_or_update_index_adds_to_an_existing_index_incrementally(app) -> None:
    course = Course(id="vec-test-5")

    with app.app_context():
        first_path = build_or_update_index(course, _chunks("First batch chunk."), _CONFIG)
        course.vector_index_path = first_path

        second_path = build_or_update_index(course, _chunks("Second batch chunk."), _CONFIG)
        assert second_path == first_path
        course.vector_index_path = second_path

        result = query(course, ["anything"], _CONFIG, top_k=10)

    assert len(result[0]) == 2


def test_delete_vector_index_removes_index_and_metadata_files(app) -> None:
    course = Course(id="vec-test-6")

    with app.app_context():
        path = build_or_update_index(course, _chunks("A chunk to delete."), _CONFIG)
        absolute_index = Path(app.instance_path) / path
        absolute_metadata = absolute_index.with_suffix(".json")
        assert absolute_index.exists()
        assert absolute_metadata.exists()

        delete_vector_index(path)

        assert not absolute_index.exists()
        assert not absolute_metadata.exists()


def test_delete_vector_index_is_a_no_op_for_a_missing_file(app) -> None:
    with app.app_context():
        delete_vector_index("vector_indexes/does-not-exist.faiss")
