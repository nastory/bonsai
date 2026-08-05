"""Per-course vector store for document-grounded retrieval (see design.md's hybrid storage model).

One FAISS index per course (not per document - a course's modules should be
able to draw from every attached source material jointly), stored on disk
alongside a small JSON metadata sidecar (FAISS itself only stores vectors +
integer ids, not arbitrary text/citation metadata). Mirrors
content_storage.py/source_material_storage.py's file-on-disk-plus-DB-path
pattern (instance-relative paths, resolved the same way
load_source_material_text() does), just with two paired files (index +
metadata) instead of one.

A flat, exact-search index (IndexFlatIP over L2-normalized vectors, i.e.
cosine similarity) - deliberate: a single local user's per-course chunk
count (tens to low hundreds even for a large document) is trivially fast
with brute-force search, so an approximate index (IVF/HNSW) would be
unjustified complexity at this scale.
"""

import json
from pathlib import Path

import faiss
import numpy as np
from flask import current_app

from app.models import Course
from app.services.document_chunking import Chunk
from app.services.embedding import embed

VECTOR_INDEX_SUBDIR = "vector_indexes"


def build_or_update_index(course: Course, chunks: list[Chunk], config: dict) -> str:
    """Embed and add chunks to a course's vector index, creating it if it doesn't exist yet.

    A course can gain source materials across multiple ingestion calls (a
    learner can attach a document mid-interview, not just at course
    creation), so this loads any existing index first (via
    course.vector_index_path) and appends rather than overwriting - each
    call's chunks get fresh, never-reused ids.

    Args:
        course: The course the chunks belong to. Does not write the
            resulting path back onto the model - the caller persists it.
        chunks: The chunks to add (e.g. from document_chunking.chunk_pages()).
        config: kwargs for embedding.embed(), from resolve_embedding_config().

    Returns:
        The index file's path, relative to instance_path, for storing on
        Course.vector_index_path.
    """
    vectors = np.array(embed([c.text for c in chunks], **config), dtype="float32")
    faiss.normalize_L2(vectors)

    if course.vector_index_path:
        index_path = _resolve(course.vector_index_path)
        metadata_path = index_path.with_suffix(".json")
        index = faiss.read_index(str(index_path))
        metadata: dict[str, dict] = json.loads(metadata_path.read_text())
    else:
        relative_path = Path(VECTOR_INDEX_SUBDIR) / f"{course.id}.faiss"
        index_path = _resolve(str(relative_path))
        metadata_path = index_path.with_suffix(".json")
        index = faiss.IndexIDMap(faiss.IndexFlatIP(vectors.shape[1]))
        metadata = {}

    next_id = max((int(k) for k in metadata), default=-1) + 1
    ids = np.arange(next_id, next_id + len(chunks))
    index.add_with_ids(vectors, ids)
    for chunk_id, chunk in zip(ids, chunks):
        metadata[str(int(chunk_id))] = {
            "text": chunk.text,
            "source": chunk.source,
            "page": chunk.page,
            "url": chunk.url,
        }

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    metadata_path.write_text(json.dumps(metadata))
    return course.vector_index_path or str(Path(VECTOR_INDEX_SUBDIR) / f"{course.id}.faiss")


def query(course: Course, query_texts: list[str], config: dict, top_k: int) -> dict[int, list[Chunk]]:
    """Retrieve the most relevant chunks for each of a list of queries.

    Every query is embedded in one batched call, then searched against the
    course's index locally (no I/O per query - unlike Tavily web search,
    there's no network round-trip here, so no threading is needed the way
    module_retrieval.py's retrieve_for_module() uses it).

    Args:
        course: The course to search. If it has no vector_index_path yet
            (no source materials ingested, or ingestion predates this
            feature), every query maps to an empty list.
        query_texts: The queries, e.g. one per activity in a module.
        config: kwargs for embedding.embed(), from resolve_embedding_config().
        top_k: How many chunks to return per query.

    Returns:
        A dict mapping each query's index (in query_texts) to its ranked
        list of Chunks, closest match first.
    """
    if not course.vector_index_path:
        return {i: [] for i in range(len(query_texts))}

    index_path = _resolve(course.vector_index_path)
    metadata_path = index_path.with_suffix(".json")
    index = faiss.read_index(str(index_path))
    metadata: dict[str, dict] = json.loads(metadata_path.read_text())

    vectors = np.array(embed(query_texts, **config), dtype="float32")
    faiss.normalize_L2(vectors)

    k = min(top_k, index.ntotal)
    if k == 0:
        return {i: [] for i in range(len(query_texts))}

    _, ids = index.search(vectors, k)
    return {
        i: [_chunk_from_metadata(metadata[str(chunk_id)]) for chunk_id in row if chunk_id != -1]
        for i, row in enumerate(ids)
    }


def rank_chunks(chunks: list[Chunk], query_text: str, config: dict, top_k: int) -> list[Chunk]:
    """Rank a list of chunks by similarity to a query, without touching any persisted index.

    For scoring a single, just-ingested document's own chunks against a
    query (e.g. course_context.py's summarize_document_for_interview()) -
    querying the course's persisted index instead would blend in every
    other attached source material's chunks too, which isn't what a
    per-document summary wants.

    Args:
        chunks: The chunks to rank, e.g. from document_chunking.chunk_pages()
            for one just-ingested document.
        query_text: The query to rank against.
        config: kwargs for embedding.embed(), from resolve_embedding_config().
        top_k: How many chunks to return.

    Returns:
        The top_k highest-scoring chunks, closest match first.
    """
    if not chunks:
        return []

    vectors = np.array(embed([c.text for c in chunks], **config), dtype="float32")
    faiss.normalize_L2(vectors)
    query_vector = np.array(embed([query_text], **config), dtype="float32")
    faiss.normalize_L2(query_vector)

    scores = vectors @ query_vector[0]
    top_indices = np.argsort(-scores)[:top_k]
    return [chunks[i] for i in top_indices]


def delete_vector_index(vector_index_path: str) -> None:
    """Delete a course's vector index and metadata sidecar, e.g. when its course is deleted.

    Args:
        vector_index_path: The path stored in Course.vector_index_path,
            relative to instance_path (or absolute). Missing files are
            ignored rather than erroring, since this is cleanup, not a
            load a caller depends on succeeding.
    """
    index_path = _resolve(vector_index_path)
    index_path.unlink(missing_ok=True)
    index_path.with_suffix(".json").unlink(missing_ok=True)


def _resolve(path: str) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path(current_app.instance_path) / resolved
    return resolved


def _chunk_from_metadata(entry: dict) -> Chunk:
    return Chunk(text=entry["text"], source=entry["source"], page=entry["page"], url=entry.get("url"))
