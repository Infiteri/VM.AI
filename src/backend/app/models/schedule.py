from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Text
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
    start = Column(DateTime(timezone=True), nullable=False)  # Slot start time
    end = Column(DateTime(timezone=True), nullable=False)  # Slot end time
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
    start = Column(DateTime(timezone=True), nullable=False)  # Slot start time
    end = Column(DateTime(timezone=True), nullable=False)  # Slot end time
    value = Column(Float, nullable=True)  # Task value
    fixed = Column(Boolean, default=False, nullable=False)  # Cannot be displaced
    location = Column(Text, nullable=True)  # For location continuity

    # Relationships
    task = relationship(
        "Task",
        back_populates="provisional_slots",
        lazy="select",
    )
