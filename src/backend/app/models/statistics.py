from sqlalchemy import Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class TaskStatistics(BaseModel):
    """
    Task-level behavioral data.

    Updated by Stats Recorder. Read by Enrichment, Task Matching, Scheduler.
    Rows are NEVER cascade-deleted when a task is deleted (persist for matching).
    """

    __tablename__ = "task_statistics"

    task_name = Column(Text, nullable=False, unique=True)
    task_name_vector = Column(ARRAY(Float), nullable=True)  # 384-dim MiniLM embedding

    # Plan averages keyed by difficulty bucket (0.0, 0.5, 1.0)
    # Structure: {"0.0": {"count": 5, "avg": 30}, "0.5": {"count": 3, "avg": 45}, "1.0": {"count": 4, "avg": 45}}
    # - count: number of records for this bucket
    # - avg: average duration in minutes for this bucket
    avg_duration = Column(JSONB, nullable=True)
    avg_duration_delta = Column(JSONB, nullable=True)

    avg_difficulty = Column(Float, nullable=True)  # 0.0–1.0
    avg_difficulty_delta = Column(Float, nullable=True)

    # Counters
    completed_count = Column(Integer, default=0, nullable=False)
    uncompleted_count = Column(Integer, default=0, nullable=False)
    records = Column(Integer, default=0, nullable=False)

    # Time preferences (kept as JSONB — sparse time series)
    task_time_scores = Column(JSONB, nullable=True)

    # Relationships
    tasks = relationship(
        "Task",
        foreign_keys="[Task.task_statistics_id]",
        back_populates="statistics",
        lazy="select",
    )
    associated_tasks = relationship(
        "Task",
        foreign_keys="[Task.associated_task_statistics_id]",
        overlaps="associated_statistics",  # Silence warning about FK overlap
        lazy="select",
    )
    locations = relationship(
        "TaskStatisticsLocation",
        back_populates="statistics",
        cascade="all, delete-orphan",
        lazy="select",
    )


class CategoryStatistics(BaseModel):
    """
    Category-level behavioral aggregates.

    Pre-seeded with: study, fitness, work, personal.
    Used by Enrichment as fallback when no task-level stats exist.
    """

    __tablename__ = "category_statistics"

    # Use BaseModel's UUID id (no override)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Plan averages keyed by difficulty bucket (0.0, 0.5, 1.0)
    # Structure: {"0.0": {"count": 5, "avg": 30}, "0.5": {"count": 3, "avg": 45}, "1.0": {"count": 4, "avg": 45}}
    # - count: number of records for this bucket
    # - avg: average duration in minutes for this bucket
    avg_duration = Column(JSONB, nullable=True)
    avg_duration_delta = Column(
        JSONB, nullable=True
    )  # Structure: {"0.5": {"count": 3, "avg": 10}, "1.0": {"count": 2, "avg": 15}}
    avg_difficulty = Column(Float, nullable=True)
    avg_difficulty_delta = Column(Float, nullable=True)

    # Counters
    completed_count = Column(Integer, default=0, nullable=False)
    uncompleted_count = Column(Integer, default=0, nullable=False)
    records = Column(Integer, default=0, nullable=False)

    # Time preferences (kept as JSONB — sparse time series)
    category_time_scores = Column(JSONB, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="statistics", lazy="select")
    locations = relationship(
        "CategoryStatisticsLocation",
        back_populates="statistics",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def name(self) -> str:
        """Backward compatible property - returns category name."""
        return self.category.name if self.category else None


class TaskStatisticsLocation(Base):
    """
    Junction table: tasks_statistics ↔ locations with count.

    Tracks how many times a task was done at each location.
    """

    __tablename__ = "task_statistics_locations"

    statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("task_statistics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    count = Column(Integer, nullable=False, default=0)

    # Relationships
    statistics = relationship(
        "TaskStatistics",
        back_populates="locations",
        lazy="select",
    )
    location = relationship(
        "Location",
        back_populates="task_statistics",
        lazy="select",
    )


class CategoryStatisticsLocation(Base):
    """
    Junction table: category_statistics ↔ locations with count.

    Tracks how many times tasks in a category were done at each location.
    """

    __tablename__ = "category_statistics_locations"

    statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("category_statistics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    count = Column(Integer, nullable=False, default=0)

    # Relationships
    statistics = relationship(
        "CategoryStatistics",
        back_populates="locations",
        lazy="select",
    )
    location = relationship(
        "Location",
        back_populates="category_statistics",
        lazy="select",
    )
