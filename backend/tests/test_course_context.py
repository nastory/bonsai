"""Tests for course-context compaction and learning-history assembly.

Runs in LLM_TEST_MODE (via the `db`/`app` fixtures) for compaction itself;
render_course_context()/assemble_learning_history() are pure formatting, so
they're tested directly against hand-built models.
"""

from app.models import ConversationMessage, Course, Module, SourceMaterial
from app.services.course_context import (
    assemble_learning_history,
    compact_course_context,
    render_course_context,
    render_source_material_summaries,
    render_source_materials,
    summarize_document_for_interview,
)
from app.services.document_chunking import Chunk
from app.services.source_material_storage import save_source_material_text


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeEmbeddingItem(dict):
    """A dict subclass so item["embedding"] works, matching litellm's real response shape."""


class _FakeEmbeddingResponse:
    def __init__(self, num_vectors: int) -> None:
        self.data = [_FakeEmbeddingItem(embedding=[0.1, 0.2, 0.3]) for _ in range(num_vectors)]


def _fake_embedding(**kwargs):
    return _FakeEmbeddingResponse(len(kwargs["input"]))


def test_summarize_document_for_interview_sends_the_document_excerpt_and_parses_the_summary(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        captured: dict = {}

        def fake_completion(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse('{"summary": "A concise summary."}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
        monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)

        chunks = [Chunk(text="GPU memory coalescing is a key optimization.", source="paper.pdf", page=1)]
        summary = summarize_document_for_interview(chunks, {"model": "test"}, {"model": "test-embedding"})

        assert summary == "A concise summary."
        assert captured["messages"][0]["role"] == "system"
        assert captured["messages"][1] == {
            "role": "user",
            "content": "Representative excerpts from the document:\n\nGPU memory coalescing is a key optimization.",
        }


def _make_course(course_id="c1", **overrides):
    defaults = dict(
        id=course_id, title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    defaults.update(overrides)
    return Course(**defaults)


def test_compact_course_context_sends_real_conversation_turns_not_flattened_text(
    real_llm_app, monkeypatch
) -> None:
    from app.extensions import db

    with real_llm_app.app_context():
        course = _make_course()
        course.modules = [
            Module(id="m1", position=0, title="Basics", description="Foundations.", estimated_timeline="1 week",
                   status="in_progress", learning_outcomes=[]),
        ]
        db.session.add_all([
            course,
            ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="I want to learn GPU programming"),
            ConversationMessage(course_id="c1", role="assistant", kind="interview_question", content="How experienced are you?"),
            ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="A total beginner"),
            ConversationMessage(course_id="c1", role="assistant", kind="outline_presented", content='{"title": "T"}'),
            ConversationMessage(course_id="c1", role="user", kind="outline_approved", content="Approved. Let's start learning."),
        ])
        db.session.commit()

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse('{"summary": "s", "learnerProfile": "p", "keyDecisions": []}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        compact_course_context(course)

        roles = [m["role"] for m in captured["messages"]]
        contents = [m["content"] for m in captured["messages"]]
        assert roles[0] == "system"
        assert "${" not in contents[0]
        assert "I want to learn GPU programming" in contents
        assert "How experienced are you?" in contents
        assert "A total beginner" in contents
        assert '{"title": "T"}' in contents
        assert "Approved. Let's start learning." in contents


def test_compact_course_context_returns_condensed_fields(db) -> None:
    course = _make_course()
    course.modules = [
        Module(id="m1", position=0, title="Basics", description="Foundations.", estimated_timeline="1 week",
               status="in_progress", learning_outcomes=[]),
    ]
    db.session.add_all([
        course,
        ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="I want to learn GPU programming"),
    ])
    db.session.commit()

    context = compact_course_context(course)

    assert context.summary
    assert context.learnerProfile
    assert context.keyDecisions == []


def test_render_course_context_returns_empty_string_when_unset(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    assert render_course_context(course) == ""


def test_render_course_context_formats_summary_learner_profile_and_decisions(db) -> None:
    course = _make_course(context_summary={
        "summary": "A course on GPU programming.",
        "learnerProfile": "Comfortable with Python, new to GPUs.",
        "keyDecisions": ["Focused on CUDA over OpenCL"],
    })
    db.session.add(course)
    db.session.commit()

    rendered = render_course_context(course)

    assert "A course on GPU programming." in rendered
    assert "Comfortable with Python, new to GPUs." in rendered
    assert "Focused on CUDA over OpenCL" in rendered


def test_render_course_context_omits_key_decisions_line_when_empty(db) -> None:
    course = _make_course(context_summary={
        "summary": "A course on GPU programming.", "learnerProfile": "A beginner.", "keyDecisions": [],
    })
    db.session.add(course)
    db.session.commit()

    assert "Key decisions" not in render_course_context(course)


def _make_source_material(course_id: str, material_id: str, file_name: str, text: str) -> SourceMaterial:
    text_path = save_source_material_text(material_id, text)
    return SourceMaterial(id=material_id, course_id=course_id, file_name=file_name, text_path=text_path)


def test_render_source_materials_returns_empty_string_when_none(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    assert render_source_materials(course) == ""


def test_render_source_materials_includes_filename_and_concatenates_multiple(db) -> None:
    course = _make_course()
    course.source_materials = [
        _make_source_material("c1", "src-1", "paper1.pdf", "First document content."),
        _make_source_material("c1", "src-2", "paper2.txt", "Second document content."),
    ]
    db.session.add(course)
    db.session.commit()

    rendered = render_source_materials(course)

    assert "paper1.pdf" in rendered
    assert "First document content." in rendered
    assert "Second document content." in rendered


def test_render_source_material_summaries_returns_empty_string_when_none(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    assert render_source_material_summaries(course) == ""


def test_render_source_material_summaries_includes_filename_and_summary(db) -> None:
    course = _make_course()
    material = _make_source_material("c1", "src-1", "paper.pdf", "GPU memory coalescing basics.")
    material.interview_summary = "A short paper about GPU memory coalescing."
    course.source_materials = [material]
    db.session.add(course)
    db.session.commit()

    rendered = render_source_material_summaries(course)

    assert "paper.pdf" in rendered
    assert "A short paper about GPU memory coalescing." in rendered
    assert "GPU memory coalescing basics." not in rendered


def test_render_source_material_summaries_skips_materials_without_a_summary_yet(db) -> None:
    course = _make_course()
    material = _make_source_material("c1", "src-1", "paper.pdf", "GPU memory coalescing basics.")
    course.source_materials = [material]
    db.session.add(course)
    db.session.commit()

    assert render_source_material_summaries(course) == ""


def test_summarize_document_for_interview_returns_mock_in_test_mode(db) -> None:
    chunks = [Chunk(text="Some document text.", source="notes.txt", page=None)]

    summary = summarize_document_for_interview(chunks, {"model": "test"}, {"model": "test-embedding"})

    assert summary == "[MOCK] Summary of the document."


def test_assemble_learning_history_returns_only_course_context_with_no_digests(db) -> None:
    course = _make_course(context_summary={
        "summary": "A course on GPU programming.", "learnerProfile": "A beginner.", "keyDecisions": [],
    })
    db.session.add(course)
    db.session.commit()

    history = assemble_learning_history(course)

    assert "A course on GPU programming." in history
    assert history == render_course_context(course)


def test_assemble_learning_history_returns_empty_string_for_course_with_nothing_yet(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    assert assemble_learning_history(course) == ""


def test_assemble_learning_history_includes_prior_module_digests_in_position_order(db) -> None:
    course = _make_course(context_summary={
        "summary": "A course on GPU programming.", "learnerProfile": "A beginner.", "keyDecisions": [],
    })
    module_1 = Module(id="m1", position=0, title="Basics", description="d", estimated_timeline="1 week",
                       status="completed", learning_outcomes=[])
    module_2 = Module(id="m2", position=1, title="Memory", description="d", estimated_timeline="1 week",
                       status="in_progress", learning_outcomes=[])
    course.modules = [module_1, module_2]
    db.session.add(course)
    db.session.commit()

    # Deliberately inserted out of module-position order, to confirm
    # assembly sorts by module position rather than insertion/id order.
    db.session.add_all([
        ConversationMessage(course_id="c1", module_id="m2", role="assistant", kind="module_learning_digest",
                             content="Digest for memory module."),
        ConversationMessage(course_id="c1", module_id="m1", role="assistant", kind="module_learning_digest",
                             content="Digest for basics module."),
    ])
    db.session.commit()

    history = assemble_learning_history(course)

    assert history.index("Digest for basics module.") < history.index("Digest for memory module.")


def test_assemble_learning_history_respects_up_to_module_position(db) -> None:
    course = _make_course()
    module_1 = Module(id="m1", position=0, title="Basics", description="d", estimated_timeline="1 week",
                       status="completed", learning_outcomes=[])
    module_2 = Module(id="m2", position=1, title="Memory", description="d", estimated_timeline="1 week",
                       status="in_progress", learning_outcomes=[])
    course.modules = [module_1, module_2]
    db.session.add(course)
    db.session.commit()

    db.session.add_all([
        ConversationMessage(course_id="c1", module_id="m1", role="assistant", kind="module_learning_digest",
                             content="Digest for basics module."),
        ConversationMessage(course_id="c1", module_id="m2", role="assistant", kind="module_learning_digest",
                             content="Digest for memory module."),
    ])
    db.session.commit()

    history = assemble_learning_history(course, up_to_module_position=0)

    assert "Digest for basics module." in history
    assert "Digest for memory module." not in history


def test_assemble_learning_history_ignores_non_digest_conversation_messages(db) -> None:
    course = _make_course()
    db.session.add_all([
        course,
        ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="I want to learn GPU programming"),
    ])
    db.session.commit()

    assert assemble_learning_history(course) == ""
