"""Tests for extracting text from uploaded source-material documents.

Fixtures are generated at test time rather than checked in as binaries:
python-docx can already write .docx files, and a minimal one-page .pdf with
real extractable text is small enough to build by hand (no reportlab/fpdf2
dependency needed just to produce test input).
"""

import io

import docx
import pytest

from app.services.document_extraction import (
    MAX_EXTRACTED_CHARS,
    TRUNCATION_MARKER,
    DocumentExtractionError,
    extract_text,
)


def _make_docx_bytes(*paragraphs: str) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _make_pdf_bytes(text: str = "Hello World") -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        None,  # filled in below once the content stream is built
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 24 Tf 10 100 Td ({text}) Tj ET".encode()
    objects[3] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"

    buf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(buf)
    buf += f"xref\n0 {len(objects) + 1}\n".encode()
    buf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(buf)


def test_extract_text_from_txt() -> None:
    result = extract_text("notes.txt", "GPU memory coalescing basics.".encode())

    assert result == "GPU memory coalescing basics."


def test_extract_text_from_txt_replaces_undecodable_bytes_instead_of_crashing() -> None:
    result = extract_text("notes.txt", b"valid text \xff\xfe more text")

    assert "valid text" in result
    assert "more text" in result


def test_extract_text_from_docx() -> None:
    content = _make_docx_bytes("Introduction to GPUs.", "Memory coalescing matters.")

    result = extract_text("paper.docx", content)

    assert "Introduction to GPUs." in result
    assert "Memory coalescing matters." in result


def test_extract_text_from_docx_raises_for_corrupt_file() -> None:
    with pytest.raises(DocumentExtractionError):
        extract_text("paper.docx", b"this is not a real docx file")


def test_extract_text_from_pdf() -> None:
    content = _make_pdf_bytes("GPU Architecture Basics")

    result = extract_text("paper.pdf", content)

    assert "GPU Architecture Basics" in result


def test_extract_text_from_pdf_raises_for_corrupt_file() -> None:
    with pytest.raises(DocumentExtractionError):
        extract_text("paper.pdf", b"this is not a real pdf file")


def test_extract_text_raises_for_unsupported_extension() -> None:
    with pytest.raises(DocumentExtractionError):
        extract_text("notes.rtf", b"some content")


def test_extract_text_raises_for_whitespace_only_result() -> None:
    with pytest.raises(DocumentExtractionError):
        extract_text("empty.txt", b"   \n\n   ")


def test_extract_text_truncates_past_max_extracted_chars() -> None:
    long_text = "a" * (MAX_EXTRACTED_CHARS + 500)

    result = extract_text("long.txt", long_text.encode())

    assert result == "a" * MAX_EXTRACTED_CHARS + TRUNCATION_MARKER


def test_extract_text_does_not_truncate_short_text() -> None:
    result = extract_text("short.txt", b"short and sweet")

    assert result == "short and sweet"
    assert TRUNCATION_MARKER not in result
