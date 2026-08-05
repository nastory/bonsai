"""Tests for module generation's legacy whole-document fallback path.

This exercises Course.source_materials present but Course.vector_index_path
absent - source materials ingested before chunking/embedding existed (or
whose embedding failed), which build_or_update_index() never populated. See
module_generation.py's _generate_activities_content()/_module_seed_data_message().
For the normal, current path (a real vector index present), see
test_module_generation_vector_retrieval.py - that one grounds each activity
in retrieved chunks rather than the whole document text, and never calls
plan_activity_searches()/retrieve_for_module() either.
"""

from app.extensions import db as _db
from app.models import Course, Module, SourceMaterial
from app.services.module_generation import generate_module_activities
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


def _make_module_with_source_material() -> Module:
    course = Course(
        id="c1",
        title="GPU Programming",
        description="A practical intro.",
        prerequisites=[],
        estimated_timeline="4 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
        stage="active",
    )
    text_path = save_source_material_text("src-1", "GPU memory coalescing improves throughput significantly.")
    course.source_materials = [SourceMaterial(id="src-1", file_name="paper.txt", text_path=text_path)]
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Getting Started",
        description="Foundational concepts.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Understand the basics"],
        activity_plan=[{"type": "reading", "title": "Intro", "plan": "Cover the basics."}],
    )
    course.modules = [module]
    _db.session.add(course)
    _db.session.commit()
    return module


def test_document_grounded_module_never_calls_search_planning_or_web_search(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_source_material()

        def fail_if_called(*args, **kwargs):
            raise AssertionError("search should not be called when the course has source materials")

        monkeypatch.setattr("app.services.module_generation.plan_activity_searches", fail_if_called)
        monkeypatch.setattr("app.services.module_retrieval.web_search", fail_if_called)

        canned = iter(
            [
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert result.activities[0].title == "Intro"


def test_document_grounded_module_seed_prompt_includes_source_material_text(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_source_material()

        captured_calls: list[list[dict]] = []
        canned = [
            '{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}',
            '{"digest": "Covered the basics."}',
        ]

        def fake_completion(**kwargs):
            captured_calls.append(kwargs["messages"])
            return _FakeResponse(canned[len(captured_calls) - 1])

        monkeypatch.setattr("app.services.llm.litellm.completion", fake_completion)

        generate_module_activities(module.id)

        # First call is activity generation: [system, user(seed data message), user(activity 1 turn)].
        seed_data_message = captured_calls[0][1]["content"]
        assert "GPU memory coalescing improves throughput significantly." in seed_data_message
        assert "paper.txt" in seed_data_message


def test_document_grounded_activity_has_no_citations_when_response_omits_them(real_llm_app, monkeypatch) -> None:
    with real_llm_app.app_context():
        module = _make_module_with_source_material()
        canned = iter(
            [
                _FakeResponse('{"type": "reading", "title": "Intro", "estimatedMinutes": 10, "body": "b"}'),
                _FakeResponse('{"digest": "Covered the basics."}'),
            ]
        )
        monkeypatch.setattr("app.services.llm.litellm.completion", lambda **kwargs: next(canned))

        result = generate_module_activities(module.id)

        assert result.activities[0].to_dict().get("citations") is None


def test_document_grounded_module_generates_successfully_under_llm_test_mode(client, db) -> None:
    course = Course(
        id="c1", title="GPU Programming", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", stage="active",
    )
    text_path = save_source_material_text("src-1", "GPU memory coalescing text.")
    course.source_materials = [SourceMaterial(id="src-1", file_name="paper.txt", text_path=text_path)]
    module = Module(
        id="m1", course_id="c1", position=0, title="Getting Started", description="d",
        estimated_timeline="1 week", status="in_progress", learning_outcomes=[],
        activity_plan=[{"type": "reading", "title": "Intro", "plan": "p"}],
    )
    course.modules = [module]
    db.session.add(course)
    db.session.commit()

    response = client.post(f"/api/modules/{module.id}/generate-activities")

    assert response.status_code == 200
    generated_module = next(m for m in response.get_json()["modules"] if m["id"] == "m1")
    assert len(generated_module["activities"]) >= 1
