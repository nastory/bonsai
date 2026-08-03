"""Tests for ConversationMessage and Course's stage/parent_course_id fields."""

from app.models import ConversationMessage, Course, Module


def _make_course(course_id="c1", **overrides):
    defaults = dict(
        id=course_id, title="T", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    defaults.update(overrides)
    return Course(**defaults)


def test_course_stage_defaults_to_active(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    assert db.session.get(Course, "c1").stage == "active"


def test_course_can_be_created_in_interview_stage(db) -> None:
    course = _make_course(stage="interview")
    db.session.add(course)
    db.session.commit()

    assert db.session.get(Course, "c1").stage == "interview"


def test_course_parent_course_id_links_to_another_course(db) -> None:
    parent = _make_course(course_id="parent")
    child = _make_course(course_id="child", parent_course_id="parent")
    db.session.add_all([parent, child])
    db.session.commit()

    assert db.session.get(Course, "child").parent_course_id == "parent"


def test_conversation_message_belongs_to_a_course(db) -> None:
    course = _make_course()
    message = ConversationMessage(
        course_id="c1", role="user", kind="interview_answer",
        content="I want to learn GPU programming",
    )
    db.session.add_all([course, message])
    db.session.commit()

    fetched = db.session.get(Course, "c1")
    assert len(fetched.conversation) == 1
    assert fetched.conversation[0].content == "I want to learn GPU programming"
    assert fetched.conversation[0].role == "user"


def test_conversation_messages_are_ordered_by_creation(db) -> None:
    course = _make_course()
    db.session.add(course)
    db.session.commit()

    db.session.add(ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="first"))
    db.session.commit()
    db.session.add(ConversationMessage(course_id="c1", role="assistant", kind="interview_question", content="second"))
    db.session.commit()

    fetched = db.session.get(Course, "c1")
    assert [m.content for m in fetched.conversation] == ["first", "second"]


def test_conversation_message_can_be_attributed_to_a_module(db) -> None:
    course = _make_course()
    module = Module(
        id="m1", course_id="c1", position=0, title="Module 1", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
    )
    message = ConversationMessage(
        course_id="c1", module_id="m1", role="assistant", kind="module_learning_digest",
        content="Covered SIMT execution and warp divergence.",
    )
    db.session.add_all([course, module, message])
    db.session.commit()

    fetched = db.session.get(ConversationMessage, message.id)
    assert fetched.module_id == "m1"


def test_conversation_message_module_id_defaults_to_none(db) -> None:
    course = _make_course()
    message = ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="hi")
    db.session.add_all([course, message])
    db.session.commit()

    assert db.session.get(ConversationMessage, message.id).module_id is None


def test_deleting_course_cascades_to_conversation_messages(db) -> None:
    course = _make_course()
    message = ConversationMessage(course_id="c1", role="user", kind="interview_answer", content="hi")
    db.session.add_all([course, message])
    db.session.commit()
    message_id = message.id

    db.session.delete(course)
    db.session.commit()

    assert db.session.get(ConversationMessage, message_id) is None
