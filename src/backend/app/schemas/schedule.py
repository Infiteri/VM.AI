from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from uuid import UUID
from app.schemas.shared import SuccessResponse
from app.schemas.task import TaskDetailResponse


class ScheduleTask(BaseModel):
    """A single task shown on the calendar for a specific day."""
    task_id: UUID
    name: str
    start: datetime
    end: datetime
    location: str  # Not optional
    rated: bool


class ScheduleResponse(BaseModel):
    """Response for GET /schedule"""
    date: date  # Strict date type
    tasks: List[ScheduleTask]


class BatchScheduleResponse(BaseModel):
    """Response for POST /schedule/batch"""
    success: bool
    scheduled_count: int
    unscheduled_remaining: List[TaskDetailResponse]  # Changed to TaskDetailResponse
    message: str
    provisional_changes: List[dict]
    execution_time_ms: int


# ---------------------------------------------------------
# Provisional Schemas
# ---------------------------------------------------------

class ProvisionalChange(BaseModel):
    """A single pending change in the schedule."""
    task_id: UUID
    task_name: str
    change_type: Optional[str] = None
    new_slot_start: datetime
    new_slot_end: datetime
    location: str  # Not optional

    # Removed: id, value, fixed (as requested)


class ProvisionalChangesResponse(BaseModel):
    """Response for GET /provisional/changes"""
    changes: List[ProvisionalChange]
    total_count: int


class ProvisionalResetResponse(SuccessResponse):
    """Response for POST /provisional/reset"""
    changes_discarded: int


class ProvisionalCommitResponse(SuccessResponse):
    """Response for POST /provisional/commit"""
    committed_count: int
    transaction_time_ms: int
