"""One-off maintenance: rebuild the vector index for any course that has
uploaded source materials but no vector index yet.

Found via a real, live bug in this dev database: a course with a real
uploaded document (and real generated content grounded in it) had
`Course.vector_index_path` stuck at None, so Ask Me Anything's candidate
filter (`vector_index_path IS NOT NULL`) silently excluded it from every
classification - no error, just quietly unreachable. The likely cause was
two backend processes briefly listening on the same port during an earlier
debugging session, racing on the same course row's commit (see design.md's
AMA "Post-ship fix" entries) - not a bug in the ingestion code itself
(_ingest_source_materials() does set and commit this field correctly, per
its own passing tests), but the fix doesn't need re-uploading either way:
SourceMaterial.text_path already holds the extracted text, so this just
re-chunks and re-embeds it.

No page numbers: the stored text is already flattened (extract_text()'s
output, not extract_pages()'s page-structured one - that structure is lost
once flattened), so this chunks it as a single unpaginated page, the same
way .txt/.docx sources already work (Chunk.page=None). Citations for a
backfilled document show the filename only, not "filename, p. N".

Run with: python backfill_vector_indexes.py
"""

from app import create_app
from app.extensions import db
from app.models import Course
from app.services.document_chunking import chunk_pages
from app.services.model_selection import EmbeddingNotConfiguredError, resolve_embedding_config
from app.services.source_material_storage import load_source_material_text
from app.services.vector_store import build_or_update_index

app = create_app(test=False, in_memory_db=False)

with app.app_context():
    try:
        embedding_config = resolve_embedding_config()
    except EmbeddingNotConfiguredError:
        print("No embedding model configured - set one in Settings first.")
        raise SystemExit(1)

    courses = list(db.session.execute(db.select(Course)).scalars())
    candidates = [c for c in courses if c.source_materials and not c.vector_index_path]

    if not candidates:
        print("Nothing to backfill - every course with source materials already has a vector index.")
        raise SystemExit(0)

    for course in candidates:
        print(f"Backfilling '{course.title}' ({course.id})...")
        chunks = []
        try:
            for material in course.source_materials:
                text = load_source_material_text(material.text_path)
                chunks.extend(chunk_pages(material.file_name, [(None, text)]))
        except FileNotFoundError as e:
            # A stale SourceMaterial row pointing at a file that no longer
            # exists (e.g. an old seed-data fixture) - skip this course
            # rather than losing the whole run over one bad row.
            print(f"  -> skipped: {e}")
            continue
        course.vector_index_path = build_or_update_index(course, chunks, embedding_config)
        db.session.commit()
        print(f"  -> indexed {len(chunks)} chunks at {course.vector_index_path}")
