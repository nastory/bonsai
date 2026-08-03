"""Tests for the Course/Module/Activity persistence models."""

from app.models import Activity, Course, Module, SourceMaterial


def test_create_course_with_modules_and_activities(db) -> None:
    course = Course(
        id="gpu-programming",
        title="GPU Programming for ML Engineers",
        description="A practical path through GPU architecture.",
        prerequisites=["Comfortable with Python"],
        estimated_timeline="6 weeks",
        thumbnail_url="from-emerald-950 to-emerald-800",
    )
    module = Module(
        id="module-1",
        course_id="gpu-programming",
        position=0,
        title="GPU Architecture Fundamentals",
        description="What a GPU actually is.",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=["Explain SIMT"],
    )
    activity = Activity(
        id="m1-a1",
        module_id="module-1",
        position=0,
        activity_type="reading",
        title="What Is a GPU, Really?",
        status="available",
        estimated_minutes=15,
    )

    db.session.add_all([course, module, activity])
    db.session.commit()

    fetched = db.session.get(Course, "gpu-programming")
    assert fetched is not None
    assert fetched.title == "GPU Programming for ML Engineers"
    assert fetched.prerequisites == ["Comfortable with Python"]
    assert len(fetched.modules) == 1
    assert fetched.modules[0].title == "GPU Architecture Fundamentals"
    assert len(fetched.modules[0].activities) == 1
    assert fetched.modules[0].activities[0].title == "What Is a GPU, Really?"


def test_module_activity_plan_defaults_to_empty_list(db) -> None:
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    module = Module(
        id="m1", course_id="c1", position=0, title="Module 1", description="d",
        estimated_timeline="1 week", status="locked", learning_outcomes=[],
    )
    db.session.add_all([course, module])
    db.session.commit()

    assert db.session.get(Module, "m1").activity_plan == []


def test_module_activity_plan_stores_planned_activities(db) -> None:
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    plan = [{"type": "reading", "title": "Intro", "plan": "Cover the basics."}]
    module = Module(
        id="m1", course_id="c1", position=0, title="Module 1", description="d",
        estimated_timeline="1 week", status="locked", learning_outcomes=[], activity_plan=plan,
    )
    db.session.add_all([course, module])
    db.session.commit()

    assert db.session.get(Module, "m1").activity_plan == plan


def test_course_context_summary_defaults_to_none(db) -> None:
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    db.session.add(course)
    db.session.commit()

    assert db.session.get(Course, "c1").context_summary is None


def test_course_context_summary_stores_compacted_memory(db) -> None:
    summary = {"summary": "A course on GPU programming.", "learnerProfile": "Comfortable with Python.", "keyDecisions": []}
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x", context_summary=summary,
    )
    db.session.add(course)
    db.session.commit()

    assert db.session.get(Course, "c1").context_summary == summary


def test_course_progress_percent_computed_from_activity_statuses(db) -> None:
    course = Course(
        id="c1",
        title="Test Course",
        description="d",
        prerequisites=[],
        estimated_timeline="1 week",
        thumbnail_url="x",
    )
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Module 1",
        description="d",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=[],
    )
    a1 = Activity(id="a1", module_id="m1", position=0, activity_type="reading", title="A1", status="completed")
    a2 = Activity(id="a2", module_id="m1", position=1, activity_type="reading", title="A2", status="available")

    db.session.add_all([course, module, a1, a2])
    db.session.commit()

    fetched = db.session.get(Course, "c1")
    assert fetched.progress_percent == 50


def test_course_progress_percent_counts_ungenerated_modules_as_estimated_remaining_work(db) -> None:
    # Otherwise a course reads as "100% done" the moment its one generated
    # module is completed, even though the rest of the course hasn't been
    # built yet. An ungenerated module (no activities) counts as an assumed
    # 5 activities of remaining work, so progress doesn't hit 100% until
    # every module is both generated and completed.
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="2 weeks", thumbnail_url="x",
    )
    module_1 = Module(
        id="m1", course_id="c1", position=0, title="Module 1", description="d",
        estimated_timeline="1 week", status="completed", learning_outcomes=[],
    )
    module_1.activities = [
        Activity(id="a1", position=0, activity_type="reading", title="A1", status="completed"),
    ]
    module_2 = Module(
        id="m2", course_id="c1", position=1, title="Module 2", description="d",
        estimated_timeline="1 week", status="locked", learning_outcomes=[],
    )
    # No activities: not generated yet.

    db.session.add_all([course, module_1, module_2])
    db.session.commit()

    fetched = db.session.get(Course, "c1")
    # 1 completed out of (1 generated + 5 estimated for the ungenerated module) = 1/6
    assert fetched.progress_percent == round(100 * 1 / 6)


def test_deleting_course_cascades_to_modules_and_activities(db) -> None:
    course = Course(
        id="c1",
        title="Test Course",
        description="d",
        prerequisites=[],
        estimated_timeline="1 week",
        thumbnail_url="x",
    )
    module = Module(
        id="m1",
        course_id="c1",
        position=0,
        title="Module 1",
        description="d",
        estimated_timeline="1 week",
        status="in_progress",
        learning_outcomes=[],
    )
    activity = Activity(id="a1", module_id="m1", position=0, activity_type="reading", title="A1", status="available")

    db.session.add_all([course, module, activity])
    db.session.commit()

    db.session.delete(course)
    db.session.commit()

    assert db.session.get(Module, "m1") is None
    assert db.session.get(Activity, "a1") is None


def test_source_material_belongs_to_a_course(db) -> None:
    course = Course(
        id="gpu-programming",
        title="GPU Programming for ML Engineers",
        description="d",
        prerequisites=[],
        estimated_timeline="6 weeks",
        thumbnail_url="x",
    )
    material = SourceMaterial(
        id="src-1",
        course_id="gpu-programming",
        file_name="Efficient-Memory-Coalescing-in-CUDA-Kernels.pdf",
        text_path="/data/source_material_text/src-1.txt",
    )

    db.session.add_all([course, material])
    db.session.commit()

    fetched = db.session.get(Course, "gpu-programming")
    assert len(fetched.source_materials) == 1
    assert fetched.source_materials[0].file_name == "Efficient-Memory-Coalescing-in-CUDA-Kernels.pdf"


def test_deleting_course_cascades_to_source_materials(db) -> None:
    course = Course(
        id="c1", title="Test Course", description="d", prerequisites=[],
        estimated_timeline="1 week", thumbnail_url="x",
    )
    material = SourceMaterial(id="src-1", course_id="c1", file_name="paper.pdf", text_path="/data/paper.txt")

    db.session.add_all([course, material])
    db.session.commit()

    db.session.delete(course)
    db.session.commit()

    assert db.session.get(SourceMaterial, "src-1") is None
