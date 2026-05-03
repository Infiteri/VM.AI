from sqlalchemy import Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class UnscheduledTask(Base):
    """
    Task queue — stores IDs of tasks awaiting scheduling.
    
    FIFO ordering (created_at). Empty queue = all tasks scheduled.
    This table has no additional data — just the task_id reference.
    
    Inherits from Base (not BaseModel) because task_id is the PK,
    not the standard id UUID. created_at is explicit for FIFO ordering.
    """
    __tablename__ = "unscheduled_tasks"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    task = relationship(
        "Task",
        back_populates="unscheduled_entry",
        lazy="select",
    )


class ScheduleChange(BaseModel):
    """
    Change log — records only 'insert' and 'move' operations.

    Tracks what changed when transforming Main → Provisional schedule.
    Cleared on atomic commit.
    """
    __tablename__ = "schedule_changes"

    provisional_schedule_slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("provisional_schedule.id", ondelete="CASCADE"),
        nullable=False,
    )
    change_type = Column(Text, nullable=False)  # 'insert' or 'move'
    old_slot_start = Column(DateTime(timezone=False), nullable=True)  # For 'move' operations
    old_slot_end = Column(DateTime(timezone=False), nullable=True)  # For 'move' operations
    new_slot_start = Column(DateTime(timezone=False), nullable=False)
    new_slot_end = Column(DateTime(timezone=False), nullable=False)

    # Relationships
    slot = relationship(
        "ProvisionalSlot",
        back_populates="schedule_changes",
        lazy="select",
    )
