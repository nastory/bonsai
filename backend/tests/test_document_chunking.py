"""Tests for splitting extracted document pages into retrieval-sized chunks."""

from app.services.document_chunking import CHUNK_OVERLAP, CHUNK_SIZE, chunk_pages


def test_chunk_pages_returns_empty_list_for_no_pages() -> None:
    assert chunk_pages("doc.txt", []) == []


def test_chunk_pages_keeps_a_short_page_as_one_chunk() -> None:
    chunks = chunk_pages("notes.txt", [(1, "GPU memory coalescing basics.")])

    assert len(chunks) == 1
    assert chunks[0].text == "GPU memory coalescing basics."
    assert chunks[0].source == "notes.txt"
    assert chunks[0].page == 1
    assert chunks[0].url is None


def test_chunk_pages_carries_source_onto_every_chunk() -> None:
    long_text = "\n\n".join(f"Paragraph {i}. " + "word " * 200 for i in range(5))

    chunks = chunk_pages("paper.pdf", [(1, long_text)])

    assert len(chunks) > 1
    assert all(c.source == "paper.pdf" for c in chunks)


def test_chunk_pages_carries_url_onto_every_chunk_when_given() -> None:
    long_text = "\n\n".join(f"Paragraph {i}. " + "word " * 200 for i in range(5))

    chunks = chunk_pages("A GPU Primer", [(None, long_text)], url="https://example.com/gpu-primer")

    assert len(chunks) > 1
    assert all(c.url == "https://example.com/gpu-primer" for c in chunks)
    assert all(c.page is None for c in chunks)


def test_chunk_pages_never_spans_two_pages() -> None:
    page_one = "First page content. " * 5
    page_two = "Second page content. " * 5

    chunks = chunk_pages("doc.pdf", [(1, page_one), (2, page_two)])

    assert all(c.page == 1 for c in chunks if "First page" in c.text)
    assert all(c.page == 2 for c in chunks if "Second page" in c.text)
    assert not any("First page" in c.text and "Second page" in c.text for c in chunks)


def test_chunk_pages_none_page_number_for_formats_without_pages() -> None:
    chunks = chunk_pages("notes.txt", [(None, "Some notes with no page concept.")])

    assert all(c.page is None for c in chunks)


def test_chunk_pages_packs_multiple_short_paragraphs_toward_chunk_size() -> None:
    paragraphs = [f"Short paragraph number {i}." for i in range(20)]
    page_text = "\n\n".join(paragraphs)

    chunks = chunk_pages("doc.txt", [(1, page_text)])

    # 20 short paragraphs should get packed into far fewer than 20 chunks.
    assert 1 <= len(chunks) < 20
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE


def test_chunk_pages_splits_an_oversized_paragraph_on_sentence_boundaries() -> None:
    sentence = "This is one reasonably long sentence about GPU architecture. "
    paragraph = sentence * (CHUNK_SIZE // len(sentence) + 5)

    chunks = chunk_pages("doc.txt", [(1, paragraph)])

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE + 2  # "\n\n" separator can push 2 chars over
    # Sentences shouldn't be cut mid-word: every chunk ends at a sentence boundary.
    assert all(chunk.text.rstrip().endswith(".") for chunk in chunks)


def test_chunk_pages_hard_splits_text_with_no_punctuation_at_all() -> None:
    run_on = "word" * (CHUNK_SIZE // 4 + 100)

    chunks = chunk_pages("doc.txt", [(1, run_on)])

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE + 2


def test_chunk_pages_consecutive_chunks_overlap() -> None:
    sentence = "This is one reasonably long sentence about GPU architecture. "
    paragraph = sentence * (CHUNK_SIZE // len(sentence) + 5)

    chunks = chunk_pages("doc.txt", [(1, paragraph)])

    assert len(chunks) > 1
    tail_of_first = chunks[0].text[-CHUNK_OVERLAP:]
    assert tail_of_first[-30:] in chunks[1].text
