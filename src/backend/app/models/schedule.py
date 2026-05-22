from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MainScheduleSlot(BaseModel):
    """
    Main committed schedule table.
    
    Source of truth for what the user sees in their calendar.
    Only populated after atomic commit from provisional_schedule.
    
    Denormalized fields (value, fixed, location) are intentionally duplicated
    from tasks table for scheduler performance — avoids JOINs during scoring.
    """
    __tablename__ = "main_schedule"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    start = Column(DateTime(timezone=False), nullable=False)  # Slot start time
    end = Column(DateTime(timezone=False), nullable=False)  # Slot end time
    value = Column(Float, nullable=True)  # Task value at scheduling time
    fixed = Column(Boolean, default=False, nullable=False)  # Cannot be displaced
    location = Column(Text, nullable=True)  # For location continuity

    # Relationships
    task = relationship(
        "Task",
        back_populates="main_schedule_slots",
        lazy="select",
    )


class ProvisionalSlot(BaseModel):
    """
    Working copy schedule — same schema as MainScheduleSlot.

    Used by Scheduler to stage changes before commit.
    Cleared and replaced by main_schedule on atomic commit.
    """
    __tablename__ = "provisional_schedule"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    start = Column(DateTime(timezone=False), nullable=False)  # Slot start time
    end = Column(DateTime(timezone=False), nullable=False)  # Slot end time
    value = Column(Float, nullable=True)  # Task value
    fixed = Column(Boolean, default=False, nullable=False)  # Cannot be displaced
    location = Column(Text, nullable=True)  # For location continuity

    __table_args__ = (
        Index("ix_prov_slot_task_id", "task_id"),
        Index("ix_prov_slot_start_end", "start", "end"),
        Index("ix_prov_slot_fixed", "fixed"),
        Index("ix_prov_slot_end", "end"),
        Index("ix_prov_slot_start", "start"),
    )

    # Relationships
    task = relationship(
        "Task",
        back_populates="provisional_slots",
        lazy="select",
    )
    schedule_changes = relationship(
        "ScheduleChange",
        back_populates="slot",
        cascade="all, delete-orphan",
        lazy="select",
    )
