from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Task(BaseModel):
    """
    Primary task storage table.
    
    Source of truth for all task definitions.
    State is derived from presence in workflow tables:
    - In unscheduled_tasks → awaiting scheduling
    - In provisional_schedule → staged for commit
    - In scheduled_slots → committed to main schedule
    """
    __tablename__ = "tasks"

    # Foreign keys to statistics tables
    task_statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks_statistics.id", ondelete="NO ACTION"),
        nullable=False,
    )
    associated_task_statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks_statistics.id", ondelete="NO ACTION"),
        nullable=True,  # Only set when matched to a similar task
    )

    # Core task fields
    name = Column(Text, nullable=False)
    start = Column(Text, nullable=True)  # ISO timestamp string (resolved by Enrichment)
    deadline = Column(Text, nullable=True)  # ISO timestamp string (resolved by Enrichment)
    difficulty = Column(Float, nullable=True)  # 0.0–1.0
    duration = Column(Integer, nullable=True)  # Minutes

    # Location (FK to normalized locations table)
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Computed values (set by Enrichment)
    importance = Column(Float, nullable=True)  # 0.0–1.0
    urgency = Column(Float, nullable=True)  # 0.0–1.0
    value = Column(Float, nullable=True)  # 0.0–1.0 (composite score)

    # Fixed-time task flags
    fixed_time = Column(Boolean, default=False, nullable=False)
    fixed_start = Column(Text, nullable=True)  # Raw time string (e.g., "Monday 09:00")

    # User rating tracking
    rated = Column(Boolean, default=False, nullable=False)

    # Relationships
    statistics = relationship(
        "TaskStatistics",
        foreign_keys=[task_statistics_id],
        lazy="select",
    )
    associated_statistics = relationship(
        "TaskStatistics",
        foreign_keys=[associated_task_statistics_id],
        lazy="select",
    )
    location = relationship(
        "Location",
        lazy="select",
    )
    task_categories = relationship(
        "TaskCategory",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
    )
    main_schedule_slots = relationship(
        "MainScheduleSlot",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
    )
    provisional_slots = relationship(
        "ProvisionalSlot",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
    )
    unscheduled_entry = relationship(
        "UnscheduledTask",
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,  # One-to-one
        lazy="select",
    )
    schedule_changes = relationship(
        "ScheduleChange",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="select",
    )
