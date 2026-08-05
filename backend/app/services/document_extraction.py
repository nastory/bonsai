"""Extracts plain text from uploaded course source materials.

Deterministic parsing, not an LLM call, so there's no LLM_TEST_MODE branch
here the way generation functions have one — tests exercise this directly
against real (if minimal) file bytes.
"""

import io
from pathlib import Path

import docx
from pypdf import PdfReader

# Ceiling applied once, here, so every downstream consumer (storage, the
# interview, the outline, module generation) only ever sees already-capped
# text rather than each needing its own truncation logic. Raised from the
# original 20_000 (~6-7 pages) now that generation is chunk-and-retrieve
# based (see document_chunking.py/vector_store.py) rather than dumping the
# whole document into one prompt - a bigger document now only costs more at
# one-time ingestion (more chunks to embed), not more risk on every
# generation call. Still a finite sanity ceiling, not unbounded: ~100-125
# pages, generous enough for the vast majority of real documents (papers,
# whitepapers, book chapters) without accepting an arbitrarily large upload.
MAX_EXTRACTED_CHARS = 500_000
TRUNCATION_MARKER = "\n[... document truncated ...]"

# (page_number, text) - page_number is 1-indexed and None for formats with
# no page concept (.txt, .docx). A page's text never spans two of these
# tuples, so document_chunking.py can always attribute a chunk to exactly
# one page for citations.
ExtractedPage = tuple[int | None, str]


class DocumentExtractionError(Exception):
    """Raised when a source material's text can't be extracted."""


def extract_pages(filename: str, content: bytes) -> list[ExtractedPage]:
    """Extract plain text from an uploaded document, one entry per page.

    Args:
        filename: The uploaded file's original name, used to pick a parser
            by extension (not the browser-supplied MIME type, which is
            inconsistent across browsers/OSes for .docx in particular).
        content: The raw file bytes.

    Returns:
        Non-empty (page_number, text) pairs, in document order. Pages with
        no extractable text (e.g. an image-only page in an otherwise
        text-having PDF) are omitted rather than returned empty.

    Raises:
        DocumentExtractionError: If the extension isn't supported, the file
            can't be parsed, or no text could be extracted from any page
            (e.g. a fully image-only PDF with no OCR support).
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        pages = [(None, _extract_txt(content))]
    elif suffix == ".docx":
        pages = [(None, _extract_docx(filename, content))]
    elif suffix == ".pdf":
        pages = _extract_pdf_pages(filename, content)
    else:
        raise DocumentExtractionError(f"Unsupported file type '{suffix}' for '{filename}'. Use .txt, .docx, or .pdf.")

    pages = [(number, text.strip()) for number, text in pages if text and text.strip()]
    if not pages:
        raise DocumentExtractionError(f"No text could be extracted from '{filename}'.")
    return pages


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded document, as one flat string.

    Args:
        filename: See extract_pages().
        content: See extract_pages().

    Returns:
        Every page's text joined with blank lines, truncated to
        MAX_EXTRACTED_CHARS with a marker appended if it was longer.

    Raises:
        DocumentExtractionError: See extract_pages().
    """
    text = "\n\n".join(page_text for _, page_text in extract_pages(filename, content))
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS] + TRUNCATION_MARKER
    return text


def _extract_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _extract_docx(filename: str, content: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as e:
        raise DocumentExtractionError(f"Couldn't read '{filename}' as a .docx file: {e}") from e
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_pdf_pages(filename: str, content: bytes) -> list[ExtractedPage]:
    try:
        reader = PdfReader(io.BytesIO(content))
        return [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
    except Exception as e:
        raise DocumentExtractionError(f"Couldn't read '{filename}' as a .pdf file: {e}") from e
