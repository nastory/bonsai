"""Tests for model to_dict() serializers.

These pin down the JSON shape the frontend will eventually consume, using
the same camelCase field names as the existing frontend TypeScript types
(see frontend/src/types/course.ts) even though the Python attributes are
snake_case.
"""

from app.models import Activity, Course, Module, SourceMaterial, UserSettings


def test_activity_to_dict_uses_camel_case_and_type_field() -> None:
    activity = Activity(
        id="a1",
        module_id="m1",
        position=0,
        activity_type="reading",
        title="What Is a GPU, Really?",
        status="completed",
        estimated_minutes=15,
    )

    assert activity.to_dict() == {
        "id": "a1",
        "type": "reading",
        "title": "What Is a GPU, Really?",
        "status": "completed",
        "estimatedMinutes": 15,
    }


def test_activity_to_dict_merges_content_from_content_path(tmp_path) -> None:
    content_file = tmp_path / "a1.json"
    content_file.write_text('{"body": "Some reading content.", "question": null}')
    activity = Activity(
        id="a1",
        module_id="m1",
        position=0,
        activity_type="reading",
        title="What Is a GPU, Really?",
        status="in_progress",
        estimated_minutes=15,
        content_path=str(content_file),
    )

    result = activity.to_dict()

    assert result["body"] == "Some reading content."
    assert result["question"] is None
    assert result["id"] == "a1"


def test_module_to_dict_includes_nested_activities() -> None:
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Module 1",
        description="d",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Explain SIMT"],
    )
    module.activities = [
        Activity(id="a1", module_id="m1", position=0, activity_type="reading", title="A1", status="completed"),
    ]

    result = module.to_dict()

    assert result["id"] == "m1"
    assert result["estimatedTimeline"] == "1 week"
    assert result["learningOutcomes"] == ["Explain SIMT"]
    assert len(result["activities"]) == 1
    assert result["activities"][0]["title"] == "A1"


def test_course_to_dict_includes_computed_progress_and_nested_modules() -> None:
    course = Course(
        id="c1",
        title="Test Course",
        description="d",
        prerequisites=["Basic Python"],
        estimated_timeline="6 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
    )
    module = Module(
        id="m1", course_id="c1", position=0, title="Module 1", description="d",
        estimated_timeline="1 week", status="completed", learning_outcomes=[],
    )
    module.activities = [
        Activity(id="a1", module_id="m1", position=0, activity_type="reading", title="A1", status="completed"),
    ]
    course.modules = [module]

    result = course.to_dict()

    assert result["thumbnailUrl"] == "from-emerald-950 to-emerald-800"
    assert result["progressPercent"] == 100
    assert result["sourceMaterials"] == []
    assert len(result["modules"]) == 1


def test_course_to_dict_includes_source_materials() -> None:
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    course.source_materials = [
        SourceMaterial(id="src-1", course_id="c1", file_name="paper.pdf", file_path="/data/paper.pdf"),
    ]

    result = course.to_dict()

    assert result["sourceMaterials"] == [{"id": "src-1", "fileName": "paper.pdf"}]


def test_user_settings_to_dict_never_echoes_the_raw_api_key() -> None:
    settings = UserSettings(
        id=1,
        name="Nigel Story",
        feedback_tone="encouraging",
        thumbnail_generation_enabled=True,
        model_provider_tier="hosted",
        model_provider_hosted_provider="anthropic",
        model_provider_api_key="sk-super-secret",
        model_provider_byom_endpoint=None,
    )

    result = settings.to_dict()

    assert result["name"] == "Nigel Story"
    assert result["modelProvider"]["tier"] == "hosted"
    assert result["modelProvider"]["hostedProvider"] == "anthropic"
    assert result["modelProvider"]["hasApiKey"] is True
    assert "apiKey" not in result["modelProvider"]


def test_user_settings_to_dict_includes_byom_endpoint_and_model() -> None:
    settings = UserSettings(
        id=1,
        name="Nigel Story",
        feedback_tone="encouraging",
        thumbnail_generation_enabled=True,
        model_provider_tier="byom",
        model_provider_byom_endpoint="http://localhost:11434",
        model_provider_byom_model="llama3",
    )

    result = settings.to_dict()

    assert result["modelProvider"]["byomEndpoint"] == "http://localhost:11434"
    assert result["modelProvider"]["byomModel"] == "llama3"


def test_user_settings_to_dict_includes_hosted_model() -> None:
    settings = UserSettings(
        id=1,
        name="Nigel Story",
        feedback_tone="encouraging",
        thumbnail_generation_enabled=True,
        model_provider_tier="hosted",
        model_provider_hosted_provider="anthropic",
        model_provider_hosted_model="claude-3-5-sonnet-20241022",
    )

    result = settings.to_dict()

    assert result["modelProvider"]["hostedModel"] == "claude-3-5-sonnet-20241022"


def test_user_settings_to_dict_includes_embedding_model() -> None:
    settings = UserSettings(id=1, embedding_model="text-embedding-3-small")

    result = settings.to_dict()

    assert result["embeddingModel"] == "text-embedding-3-small"


def test_user_settings_to_dict_embedding_model_defaults_to_none() -> None:
    settings = UserSettings(id=1)

    result = settings.to_dict()

    assert result["embeddingModel"] is None


def test_user_settings_to_dict_never_echoes_the_raw_tavily_key() -> None:
    settings = UserSettings(id=1, tavily_api_key="tvly-super-secret")

    result = settings.to_dict()

    assert result["hasTavilyApiKey"] is True
    assert "tavilyApiKey" not in result


def test_user_settings_to_dict_has_tavily_api_key_defaults_to_false() -> None:
    settings = UserSettings(id=1)

    result = settings.to_dict()

    assert result["hasTavilyApiKey"] is False
