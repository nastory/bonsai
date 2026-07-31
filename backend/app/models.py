"""SQLAlchemy models for Bonsai's course data.

Per the hybrid storage design (see design.md): this file holds structural
metadata, ordering, and progress state. The heavier generated content
(activity body text, citations, quiz options, etc.) lives in files on
disk, referenced here by Activity.content_path, not stored inline.
"""

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

    modules = db.relationship(
        "Module",
        back_populates="course",
        order_by="Module.position",
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
