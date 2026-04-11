from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel

class Task(BaseModel):
    __tablename__ = "tasks"

    task_statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks_statistics.id", ondelete="NO ACTION"),
        nullable=False,
    )
    associated_task_statistics_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks_statistics.id", ondelete="NO ACTION"),
        nullable=True,
    )

    name = Column(Text, nullable=False)
    start = Column(DateTime(timezone=True), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    difficulty = Column(Float, nullable=True)
    duration = Column(Integer, nullable=True)

    category = Column(ARRAY(Text), nullable=True)
    location = Column(Text, nullable=True)

    importance = Column(Float, nullable=True)
    urgency = Column(Float, nullable=True)
    value = Column(Float, nullable=True)

    fixed_time = Column(Boolean, default=False, nullable=False)
    fixed_start = Column(DateTime(timezone=True), nullable=True)

    rated = Column(Boolean, default=False, nullable=False)
    recurrent = Column(Boolean, default=False, nullable=False)
    recurrence_days = Column(ARRAY(Text), nullable=True)

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
    scheduled_slots = relationship(
        "ScheduledSlot",
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
        uselist=False,
        lazy="select",
    )