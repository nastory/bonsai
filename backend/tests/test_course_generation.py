"""Tests for the course-creation generation service (interview -> outline -> approve).

Runs entirely in LLM_TEST_MODE (via the `db`/`app` fixtures), so these
exercise the real control flow (question counting, stage transitions,
module creation) against deterministic canned generation output rather
than a real model.
"""

from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import ConversationMessage, Course, UserSettings
from app.services.course_generation import (
    MAX_INTERVIEW_QUESTIONS,
    CourseNotFoundError,
    approve_outline,
    delete_course,
    generate_outline,
    start_course,
    submit_interview_answer,
    submit_outline_feedback,
)
from app.services.document_extraction import DocumentExtractionError
from app.services.image_generation import ImageGenerationError


def test_start_course_creates_course_in_interview_stage(db) -> None:
    step = start_course("I want to learn GPU programming")

    assert step.course.stage == "interview"
    assert step.done is False
    assert step.question is not None


def test_start_course_records_the_first_message(db) -> None:
    step = start_course("I want to learn GPU programming")

    contents = [m.content for m in step.course.conversation]
    assert "I want to learn GPU programming" in contents


def test_start_course_with_a_file_persists_a_source_material(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert len(step.course.source_materials) == 1
    assert step.course.source_materials[0].file_name == "notes.txt"


def test_start_course_with_a_file_computes_an_interview_summary(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert step.course.source_materials[0].interview_summary == "[MOCK] Summary of the document."


def test_start_course_with_parent_course_id_sets_lineage(db) -> None:
    parent = start_course("I want to learn GPU programming").course

    step = start_course("I want to go deeper on memory coalescing", parent_course_id=parent.id)

    assert step.course.parent_course_id == parent.id


def test_start_course_raises_for_unknown_parent_course_id(db) -> None:
    with pytest.raises(CourseNotFoundError):
        start_course("I want to go deeper", parent_course_id="does-not-exist")


def test_start_course_with_an_unparseable_file_persists_nothing(db) -> None:
    file = FileStorage(stream=BytesIO(b"not a real docx"), filename="notes.docx")

    with pytest.raises(DocumentExtractionError):
        start_course("I want to learn about this paper", files=[file])


def test_interview_question_reflects_an_attached_source_material(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert "notes.txt" in (step.question or "")


def test_attaching_a_document_builds_the_course_vector_index(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert step.course.vector_index_path is not None
    assert step.course.vector_index_path.endswith(f"{step.course.id}.faiss")


def test_start_course_with_multiple_files_persists_all_source_materials(db) -> None:
    file1 = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes1.txt")
    file2 = FileStorage(stream=BytesIO(b"Warp scheduling determines thread execution order."), filename="notes2.txt")

    step = start_course("I want to learn about these papers", files=[file1, file2])

    assert len(step.course.source_materials) == 2
    assert {m.file_name for m in step.course.source_materials} == {"notes1.txt", "notes2.txt"}
    assert all(m.interview_summary for m in step.course.source_materials)


def test_multiple_documents_in_one_call_share_a_single_vector_index(db) -> None:
    file1 = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes1.txt")
    file2 = FileStorage(stream=BytesIO(b"Warp scheduling determines thread execution order."), filename="notes2.txt")

    step = start_course("I want to learn about these papers", files=[file1, file2])

    from app.services.model_selection import resolve_embedding_config
    from app.services.vector_store import query

    results = query(step.course, ["anything"], resolve_embedding_config(), top_k=10)
    file_names = {chunk.source for chunk in results[0]}

    assert file_names == {"notes1.txt", "notes2.txt"}


def test_attaching_a_second_document_on_a_later_turn_appends_to_the_same_index(db) -> None:
    file1 = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes1.txt")
    step = start_course("I want to learn about this paper", files=[file1])
    first_index_path = step.course.vector_index_path

    file2 = FileStorage(stream=BytesIO(b"Warp scheduling determines thread execution order."), filename="notes2.txt")
    step2 = submit_interview_answer(step.course.id, "here's another paper", files=[file2])

    assert step2.course.vector_index_path == first_index_path
    assert len(step2.course.source_materials) == 2

    from app.services.model_selection import resolve_embedding_config
    from app.services.vector_store import query

    results = query(step2.course, ["anything"], resolve_embedding_config(), top_k=10)
    file_names = {chunk.source for chunk in results[0]}
    assert file_names == {"notes1.txt", "notes2.txt"}


def test_start_course_web_search_supplement_defaults_to_off(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file])

    assert step.course.web_search_supplement_enabled is False


def test_start_course_can_opt_into_web_search_supplement(db) -> None:
    file = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes.txt")

    step = start_course("I want to learn about this paper", files=[file], supplement_with_web_search=True)

    assert step.course.web_search_supplement_enabled is True


def test_web_search_supplement_opt_in_is_or_in_not_overwritten(db) -> None:
    file1 = FileStorage(stream=BytesIO(b"GPU memory coalescing improves throughput."), filename="notes1.txt")
    step = start_course("I want to learn about this paper", files=[file1], supplement_with_web_search=True)

    file2 = FileStorage(stream=BytesIO(b"Warp scheduling determines thread execution order."), filename="notes2.txt")
    step2 = submit_interview_answer(
        step.course.id, "here's another paper", files=[file2], supplement_with_web_search=False
    )

    assert step2.course.web_search_supplement_enabled is True


def test_interview_question_is_generic_without_a_source_material(db) -> None:
    step = start_course("I want to learn GPU programming")

    assert "notes.txt" not in (step.question or "")


def test_submit_interview_answer_asks_another_question(db) -> None:
    step = start_course("I want to learn GPU programming")

    step2 = submit_interview_answer(step.course.id, "I'm a beginner")

    assert step2.done is False
    assert step2.question is not None
    assert step2.question != step.question


def test_submit_interview_answer_raises_for_unknown_course(db) -> None:
    with pytest.raises(CourseNotFoundError):
        submit_interview_answer("does-not-exist", "answer")


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


def test_interview_prompt_uses_document_summary_not_raw_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        from app.models import UserSettings

        UserSettings.get_or_create().embedding_model = "test-embedding"
        db.session.commit()

        # start_course() with a file makes two real completion calls in
        # order: summarize the document (ingestion), then ask the first
        # interview question. Embedding calls (chunking/indexing, and
        # ranking chunks for the summary) go through _fake_embedding instead.
        responses = [
            _FakeResponse('{"summary": "A short paper about GPU memory coalescing."}'),
            _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        ]
        captured: dict = {}

        def fake_completion(**kwargs):
            response = responses.pop(0)
            if not responses:
                captured["prompt"] = kwargs["messages"][0]["content"]
            return response

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)
        monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
        file = FileStorage(
            stream=BytesIO(b"GPU memory coalescing is a key optimization technique."), filename="notes.txt"
        )

        start_course("I want to learn about this paper", files=[file])

        assert "notes.txt" in captured["prompt"]
        assert "A short paper about GPU memory coalescing." in captured["prompt"]
        assert "GPU memory coalescing is a key optimization technique." not in captured["prompt"]


def test_interview_sends_real_conversation_turns_not_flattened_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        responses = iter(
            [
                _FakeResponse('{"coverage": "open", "done": false, "question": "What is your experience with GPUs?"}'),
                _FakeResponse('{"coverage": "open", "done": false, "question": "another question"}'),
            ]
        )
        captured: list = []

        def fake_completion(**kwargs):
            captured.append(kwargs["messages"])
            return next(responses)

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        step = start_course("I want to learn GPU programming")
        submit_interview_answer(step.course.id, "I'm a total beginner")

        second_call_messages = captured[1]
        assert second_call_messages[0]["role"] == "system"
        assert "${" not in second_call_messages[0]["content"]
        assert second_call_messages[1] == {"role": "user", "content": "I want to learn GPU programming"}
        assert second_call_messages[2] == {"role": "assistant", "content": "What is your experience with GPUs?"}
        assert second_call_messages[3] == {"role": "user", "content": "I'm a total beginner"}


def test_interview_prompt_includes_parent_context_when_branched(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        parent = Course(
            id="parent-1",
            title="GPU Programming",
            description="d",
            prerequisites=[],
            estimated_timeline="4 weeks",
            thumbnail_url="x",
            stage="active",
            context_summary={
                "summary": "Covered GPU memory coalescing basics.",
                "learnerProfile": "A beginner.",
                "keyDecisions": [],
            },
        )
        db.session.add(parent)
        db.session.commit()

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        start_course("I want to go deeper on this", parent_course_id="parent-1")

        assert "Covered GPU memory coalescing basics." in captured["prompt"]


def test_interview_prompt_omits_parent_context_when_not_branched(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}')

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        start_course("I want to learn GPU programming")

        assert "${" not in captured["prompt"]


def test_outline_prompt_includes_parent_context_when_branched(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        parent = Course(
            id="parent-1",
            title="GPU Programming",
            description="d",
            prerequisites=[],
            estimated_timeline="4 weeks",
            thumbnail_url="x",
            stage="active",
            context_summary={
                "summary": "Covered GPU memory coalescing basics.",
                "learnerProfile": "A beginner.",
                "keyDecisions": [],
            },
        )
        db.session.add(parent)
        db.session.commit()

        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        )
        step = start_course("I want to go deeper on this", parent_course_id="parent-1")

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse(
                '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_outline(step.course.id)

        assert "Covered GPU memory coalescing basics." in captured["prompt"]


def test_outline_prompt_includes_source_material_summary_not_raw_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        from app.models import UserSettings

        UserSettings.get_or_create().embedding_model = "test-embedding"
        db.session.commit()

        responses = [
            _FakeResponse('{"summary": "A short paper about GPU memory coalescing."}'),
            _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        ]
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: responses.pop(0))
        monkeypatch.setattr("app.services.embedding.litellm.embedding", _fake_embedding)
        file = FileStorage(
            stream=BytesIO(b"GPU memory coalescing is a key optimization technique."), filename="notes.txt"
        )
        step = start_course("I want to learn about this paper", files=[file])

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return _FakeResponse(
                '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_outline(step.course.id)

        assert "notes.txt" in captured["prompt"]
        assert "A short paper about GPU memory coalescing." in captured["prompt"]
        assert "GPU memory coalescing is a key optimization technique." not in captured["prompt"]


def test_outline_regeneration_includes_prior_outline_and_revision_request_as_turns(
    real_llm_app, monkeypatch
) -> None:
    with real_llm_app.app_context():
        responses = [
            _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
            _FakeResponse(
                '{"title": "T", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            ),
        ]
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: responses.pop(0))
        step = start_course("I want to learn GPU programming")
        generate_outline(step.course.id)

        captured: dict = {}

        def fake_completion(**kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse(
                '{"title": "T2", "description": "d", "prerequisites": [], "estimatedTimeline": "1 week", "modules": []}'
            )

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        submit_outline_feedback(step.course.id, "Make it shorter")

        roles = [m["role"] for m in captured["messages"]]
        contents = [m["content"] for m in captured["messages"]]
        assert roles[0] == "system"
        assert "I want to learn GPU programming" in contents
        assert any('"title":"T"' in c for c in contents)  # the previously presented outline, as a turn
        assert "Make it shorter" in contents


def test_interview_stops_after_max_questions(db) -> None:
    step = start_course("I want to learn GPU programming")
    course_id = step.course.id

    for _ in range(MAX_INTERVIEW_QUESTIONS):
        step = submit_interview_answer(course_id, "some answer")

    assert step.done is True
    assert step.question is None


def test_interview_hard_stops_at_max_questions_without_calling_the_model(real_llm_app, monkeypatch) -> None:
    """The max-question cap is enforced in code, not just left to the prompt's instruction."""
    with real_llm_app.app_context():
        monkeypatch.setattr(
            "app.services.llm.litellm.completion",
            lambda **kwargs: _FakeResponse('{"coverage": "open", "done": false, "question": "a question"}'),
        )
        step = start_course("I want to learn GPU programming")
        course_id = step.course.id

        for i in range(MAX_INTERVIEW_QUESTIONS - 1):
            db.session.add(
                ConversationMessage(
                    course_id=course_id, role="assistant", kind="interview_question", content=f"q{i}"
                )
            )
        db.session.commit()

        def fail_if_called(**kwargs):
            raise AssertionError("the model should not be called once the max question count is reached")

        monkeypatch.setattr("app.services.llm.litellm.completion", fail_if_called)

        step = submit_interview_answer(course_id, "final answer")

        assert step.done is True
        assert step.question is None


def test_generate_outline_creates_modules_and_moves_to_outline_review(db) -> None:
    step = start_course("I want to learn GPU programming")

    course = generate_outline(step.course.id)

    assert course.stage == "outline_review"
    assert len(course.modules) > 0
    assert course.title != "New Course"
    assert all(m.status == "locked" for m in course.modules)


def test_generate_outline_populates_each_module_activity_plan(db) -> None:
    step = start_course("I want to learn GPU programming")

    course = generate_outline(step.course.id)

    assert all(len(m.activity_plan) > 0 for m in course.modules)
    first_activity = course.modules[0].activity_plan[0]
    assert set(first_activity) == {"type", "title", "plan"}


def test_submit_outline_feedback_regenerates_modules(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)
    original_title = course.title

    revised = submit_outline_feedback(course.id, "add more on memory management")

    assert revised.title != original_title
    assert any(m.kind == "outline_revision_request" for m in revised.conversation)


def test_approve_outline_activates_course_and_starts_first_module(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.stage == "active"
    assert approved.modules[0].status == "in_progress"


def test_approve_outline_compacts_and_stores_course_context(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.context_summary is not None
    assert approved.context_summary["summary"]
    assert approved.context_summary["learnerProfile"]
    assert approved.context_summary["keyDecisions"] == []


def test_approve_outline_generates_thumbnail_when_enabled(db) -> None:
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.thumbnail_image_path is not None
    assert approved.to_dict()["thumbnailImageUrl"] == f"/api/courses/{course.id}/thumbnail"


def test_approve_outline_skips_thumbnail_when_disabled(db) -> None:
    UserSettings.get_or_create().thumbnail_generation_enabled = False
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.thumbnail_image_path is None
    assert approved.to_dict()["thumbnailImageUrl"] is None


def test_approve_outline_survives_thumbnail_generation_failure(db, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.course_generation.generate_thumbnail_image",
        lambda *a, **k: (_ for _ in ()).throw(ImageGenerationError("boom")),
    )
    step = start_course("I want to learn GPU programming")
    course = generate_outline(step.course.id)

    approved = approve_outline(course.id)

    assert approved.stage == "active"
    assert approved.thumbnail_image_path is None


def test_delete_course_raises_for_unknown_course(db) -> None:
    with pytest.raises(CourseNotFoundError):
        delete_course("does-not-exist")


def test_delete_course_removes_the_course_and_its_children(app, db) -> None:
    from pathlib import Path

    from app.models import Activity, Module, SourceMaterial
    from app.services.content_storage import save_activity_content
    from app.services.source_material_storage import save_source_material_text
    from app.services.thumbnail_storage import save_thumbnail_image

    thumbnail_path = save_thumbnail_image("c1", b"fake-png-bytes")
    course = Course(
        id="c1", title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
        thumbnail_image_path=thumbnail_path,
    )
    module = Module(
        id="m1", course_id="c1", position=0, title="Basics", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    content_path = save_activity_content("a1", {"body": "content"})
    activity = Activity(
        id="a1", module_id="m1", position=0, activity_type="reading", title="Intro",
        status="available", estimated_minutes=10, content_path=content_path,
    )
    text_path = save_source_material_text("src-1", "extracted text")
    material = SourceMaterial(id="src-1", course_id="c1", file_name="paper.txt", text_path=text_path)
    module.activities = [activity]
    course.modules = [module]
    course.source_materials = [material]
    db.session.add(course)
    db.session.commit()

    content_absolute = Path(app.instance_path) / content_path
    text_absolute = Path(app.instance_path) / text_path
    thumbnail_absolute = Path(app.instance_path) / thumbnail_path
    assert content_absolute.exists()
    assert text_absolute.exists()
    assert thumbnail_absolute.exists()

    delete_course("c1")

    assert db.session.get(Course, "c1") is None
    assert db.session.get(Module, "m1") is None
    assert db.session.get(Activity, "a1") is None
    assert db.session.get(SourceMaterial, "src-1") is None
    assert not content_absolute.exists()
    assert not text_absolute.exists()
    assert not thumbnail_absolute.exists()
