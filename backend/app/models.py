"""SQLAlchemy models for Bonsai's course data.

Per the hybrid storage design (see design.md): this file holds structural
metadata, ordering, and progress state. The heavier generated content
(activity body text, citations, quiz options, etc.) lives in files on
disk, referenced here by Activity.content_path, not stored inline.
"""

from typing import Any

from app.extensions import db


class Course(db.Model):
    """A course the learner is taking, made up of an ordered list of modules."""

    __tablename__ = "courses"

    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    prerequisites = db.Column(db.JSON, nullable=False, default=list)
    estimated_timeline = db.Column(db.String, nullable=False)
    thumbnail_url = db.Column(db.String, nullable=False)
    # 'interview' -> 'outline_review' -> 'active' -> 'completed'. Courses
    # created directly (e.g. via seed.py) default to 'active' since they
    # already have a full outline; the creation flow sets 'interview' itself.
    stage = db.Column(db.String, nullable=False, default="active")
    # Self-referential: set when a course was created via "keep going / dive
    # deeper / branch off" from a completed course (that feature itself is
    # Phase 2 work; this column just makes the lineage representable now).
    parent_course_id = db.Column(db.String, db.ForeignKey("courses.id"), nullable=True)

    modules = db.relationship(
        "Module",
        back_populates="course",
        order_by="Module.position",
        cascade="all, delete-orphan",
    )
    source_materials = db.relationship(
        "SourceMaterial",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    conversation = db.relationship(
        "ConversationMessage",
        back_populates="course",
        order_by="ConversationMessage.id",
        cascade="all, delete-orphan",
    )

    @property
    def progress_percent(self) -> float:
        """Percent of activities completed across all modules.

        Computed from activity status rather than stored, so it can never
        drift out of sync with the activities it's derived from.

        Returns:
            0.0 if the course has no activities yet, otherwise the
            percentage of activities with status "completed".
        """
        activities = [a for m in self.modules for a in m.activities]
        if not activities:
            return 0.0
        completed = sum(1 for a in activities if a.status == "completed")
        return round(100 * completed / len(activities), 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape frontend/src/types/course.ts's Course expects."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "estimatedTimeline": self.estimated_timeline,
            "thumbnailUrl": self.thumbnail_url,
            "progressPercent": self.progress_percent,
            "stage": self.stage,
            "modules": [m.to_dict() for m in self.modules],
            "sourceMaterials": [s.to_dict() for s in self.source_materials],
        }


class Module(db.Model):
    """One module within a course's outline."""

    __tablename__ = "modules"

    id = db.Column(db.String, primary_key=True)
    course_id = db.Column(db.String, db.ForeignKey("courses.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    estimated_timeline = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False, default="locked")
    learning_outcomes = db.Column(db.JSON, nullable=False, default=list)

    course = db.relationship("Course", back_populates="modules")
    activities = db.relationship(
        "Activity",
        back_populates="module",
        order_by="Activity.position",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape frontend/src/types/course.ts's Module expects."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "estimatedTimeline": self.estimated_timeline,
            "status": self.status,
            "learningOutcomes": self.learning_outcomes,
            "activities": [a.to_dict() for a in self.activities],
        }


class Activity(db.Model):
    """One learning activity (reading, quiz, essay, etc.) within a module."""

    __tablename__ = "activities"

    id = db.Column(db.String, primary_key=True)
    module_id = db.Column(db.String, db.ForeignKey("modules.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    activity_type = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False, default="locked")
    estimated_minutes = db.Column(db.Integer, nullable=True)
    content_path = db.Column(db.String, nullable=True)

    module = db.relationship("Module", back_populates="activities")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape frontend/src/types/course.ts's Activity expects.

        Content-heavy fields (body, citations, question, options, prompt,
        checkPrompt) will be read from the file at content_path once
        generation exists; omitted here since nothing populates them yet.
        """
        return {
            "id": self.id,
            "type": self.activity_type,
            "title": self.title,
            "status": self.status,
            "estimatedMinutes": self.estimated_minutes,
        }


class SourceMaterial(db.Model):
    """A document the learner uploaded that a course was built from."""

    __tablename__ = "source_materials"

    id = db.Column(db.String, primary_key=True)
    course_id = db.Column(db.String, db.ForeignKey("courses.id"), nullable=False)
    file_name = db.Column(db.String, nullable=False)
    file_path = db.Column(db.String, nullable=False)

    course = db.relationship("Course", back_populates="source_materials")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape frontend/src/types/course.ts's SourceMaterial expects.

        No `url` yet: serving the underlying file for download isn't built
        in this slice.
        """
        return {
            "id": self.id,
            "fileName": self.file_name,
        }


class ConversationMessage(db.Model):
    """One message in a course's ongoing history.

    Starts at course creation (the interview) and keeps growing as the
    learner progresses: module check-ins, direction-change requests, and
    (eventually) references passed forward into courses branched off this
    one. This is Bonsai's memory of the learner's experience with a course,
    not just a transcript of the creation interview.
    """

    __tablename__ = "conversation_messages"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String, db.ForeignKey("courses.id"), nullable=False)
    role = db.Column(db.String, nullable=False)  # 'user' | 'assistant'
    # Free-form tag (e.g. "interview_answer", "outline_presented",
    # "direction_change_request") for filtering/context-assembly later,
    # not enforced as an enum so new kinds don't need a migration.
    kind = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    course = db.relationship("Course", back_populates="conversation")


class UserSettings(db.Model):
    """The learner's app-wide preferences.

    Single-row by convention: there's no multi-user concept in Bonsai, so
    this table always has exactly one row, at id=1, fetched via
    get_or_create() rather than a normal query.
    """

    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    name = db.Column(db.String, nullable=False, default="Learner")
    feedback_tone = db.Column(db.String, nullable=False, default="encouraging")
    thumbnail_generation_enabled = db.Column(db.Boolean, nullable=False, default=True)
    model_provider_tier = db.Column(db.String, nullable=False, default="hosted")
    model_provider_hosted_provider = db.Column(db.String, nullable=True)
    model_provider_hosted_model = db.Column(db.String, nullable=True)
    model_provider_api_key = db.Column(db.String, nullable=True)
    model_provider_byom_endpoint = db.Column(db.String, nullable=True)
    model_provider_byom_model = db.Column(db.String, nullable=True)
    # Independently configurable from the completion model above, per the
    # PRD's model-roles requirement. Not tied to a tier/provider of its own
    # yet since nothing (retrieval, semantic search) actually uses it yet.
    embedding_model = db.Column(db.String, nullable=True)

    @classmethod
    def get_or_create(cls) -> "UserSettings":
        """Fetch the single settings row, creating it with defaults on first use.

        Returns:
            The one UserSettings row (id=1).
        """
        settings = db.session.get(cls, 1)
        if settings is None:
            settings = cls(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the shape frontend/src/types/course.ts's UserSettings expects.

        Deliberately never includes the raw API key: `hasApiKey` stands in
        for it so the frontend can show "a key is configured" without the
        backend echoing a secret back on every read.
        """
        return {
            "name": self.name,
            "feedbackTone": self.feedback_tone,
            "thumbnailGenerationEnabled": self.thumbnail_generation_enabled,
            "modelProvider": {
                "tier": self.model_provider_tier,
                "hostedProvider": self.model_provider_hosted_provider,
                "hostedModel": self.model_provider_hosted_model,
                "byomEndpoint": self.model_provider_byom_endpoint,
                "byomModel": self.model_provider_byom_model,
                "hasApiKey": bool(self.model_provider_api_key),
            },
            "embeddingModel": self.embedding_model,
        }
