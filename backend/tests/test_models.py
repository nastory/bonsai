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
    a2 = Activity(id="a2", module_id="m1", position=1, activity_type="reading", title="A2", status="locked")

    db.session.add_all([course, module, a1, a2])
    db.session.commit()

    fetched = db.session.get(Course, "c1")
    assert fetched.progress_percent == 50.0


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
        file_path="/data/source_materials/src-1.pdf",
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
    material = SourceMaterial(id="src-1", course_id="c1", file_name="paper.pdf", file_path="/data/paper.pdf")

    db.session.add_all([course, material])
    db.session.commit()

    db.session.delete(course)
    db.session.commit()

    assert db.session.get(SourceMaterial, "src-1") is None
