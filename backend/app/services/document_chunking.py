"""Splits extracted pages - from a document or a fetched web page - into retrieval-sized chunks.

Deterministic, not an LLM call - same testing approach as document_extraction.py
(direct calls against real text, no LLM_TEST_MODE branch needed). Each chunk
stays within a single page (never spans two), so a chunk always has one
unambiguous page number for citations - see chunk_pages()'s docstring.

Also used for web search results (see module_generation.py): a web page has
no "pages", so it's chunked as a single (None, content) page, tagged with
the source's url instead of a page number - see Chunk's docstring.
"""

import re
from dataclasses import dataclass

from app.services.document_extraction import ExtractedPage

# Chars, not tokens: this codebase already sizes everything else
# (MAX_EXTRACTED_CHARS, INTERVIEW_SOURCE_MATERIAL_CHAR_BUDGET) in raw
# characters rather than pulling in a tokenizer just for approximate sizing.
CHUNK_SIZE = 1_500
CHUNK_OVERLAP = 150

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Leaves headroom in every "atomic" piece handed to _merge_with_overlap() so
# there's always room to prepend an overlap tail without exceeding CHUNK_SIZE.
_MAX_ATOMIC_PIECE = CHUNK_SIZE - CHUNK_OVERLAP


@dataclass
class Chunk:
    """One retrieval-sized piece of a source, with its citation metadata.

    `source` is a document's file name or a web page's title - whichever
    produced this chunk. `page` is set for document chunks (None for
    `.txt`/`.docx`, which have no page concept); `url` is set for web
    chunks (None for every document chunk). A chunk is never both.
    """

    text: str
    source: str
    page: int | None = None
    url: str | None = None


def chunk_pages(source: str, pages: list[ExtractedPage], url: str | None = None) -> list[Chunk]:
    """Split a source's extracted pages into overlapping, retrieval-sized chunks.

    Recursive/paragraph-aware: each page's text is split into paragraphs,
    any paragraph over the atomic-piece size is split into sentences, and
    any sentence still too long gets a hard character split as a last
    resort. Those small pieces are then greedily packed back up toward
    CHUNK_SIZE, with each new chunk (past the first) starting with a small
    overlap tail of the previous one, so an idea split across a chunk
    boundary still has some shared context on both sides. A chunk never
    spans two pages, so every chunk has exactly one page number to cite.

    Args:
        source: The document's file name, or a web page's title, carried
            onto every chunk.
        pages: The extracted (page_number, text) pairs, e.g. from
            document_extraction.extract_pages() for a document, or a single
            `[(None, content)]` for a fetched web page (no page concept).
        url: The web page's url, carried onto every chunk. None for a document.

    Returns:
        Chunks in document order.
    """
    return [
        Chunk(text=piece, source=source, page=page_number, url=url)
        for page_number, page_text in pages
        for piece in _split_page(page_text)
    ]


def _split_page(text: str) -> list[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    atomic_pieces = [piece for paragraph in paragraphs for piece in _split_to_atomic(paragraph)]
    return _merge_with_overlap(atomic_pieces)


def _split_to_atomic(text: str) -> list[str]:
    """Break text down into pieces that each individually fit within _MAX_ATOMIC_PIECE."""
    if len(text) <= _MAX_ATOMIC_PIECE:
        return [text]

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if len(sentences) > 1:
        return [piece for sentence in sentences for piece in _split_to_atomic(sentence)]

    # No sentence boundary found (a single run-on sentence, or text with no
    # punctuation at all) - hard character split, the last-resort fallback.
    return [text[i : i + _MAX_ATOMIC_PIECE] for i in range(0, len(text), _MAX_ATOMIC_PIECE)]


def _merge_with_overlap(pieces: list[str]) -> list[str]:
    """Greedily pack small pieces up toward CHUNK_SIZE, each new chunk (past the first) starting with an overlap tail of the previous one."""
    if not pieces:
        return []

    chunks: list[str] = []
    current = pieces[0]
    for piece in pieces[1:]:
        candidate = f"{current}\n\n{piece}"
        if len(candidate) <= CHUNK_SIZE:
            current = candidate
            continue
        chunks.append(current)
        overlap = current[-CHUNK_OVERLAP:]
        current = f"{overlap}\n\n{piece}"
    chunks.append(current)
    return chunks
