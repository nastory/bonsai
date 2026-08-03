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
# text rather than each needing its own truncation logic.
MAX_EXTRACTED_CHARS = 20_000
TRUNCATION_MARKER = "\n[... document truncated ...]"


class DocumentExtractionError(Exception):
    """Raised when a source material's text can't be extracted."""


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded document.

    Args:
        filename: The uploaded file's original name, used to pick a parser
            by extension (not the browser-supplied MIME type, which is
            inconsistent across browsers/OSes for .docx in particular).
        content: The raw file bytes.

    Returns:
        The extracted text, truncated to MAX_EXTRACTED_CHARS with a marker
        appended if it was longer.

    Raises:
        DocumentExtractionError: If the extension isn't supported, the file
            can't be parsed, or no text could be extracted (e.g. an
            image-only PDF with no OCR support).
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        text = _extract_txt(content)
    elif suffix == ".docx":
        text = _extract_docx(filename, content)
    elif suffix == ".pdf":
        text = _extract_pdf(filename, content)
    else:
        raise DocumentExtractionError(f"Unsupported file type '{suffix}' for '{filename}'. Use .txt, .docx, or .pdf.")

    text = text.strip()
    if not text:
        raise DocumentExtractionError(f"No text could be extracted from '{filename}'.")

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


def _extract_pdf(filename: str, content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise DocumentExtractionError(f"Couldn't read '{filename}' as a .pdf file: {e}") from e
