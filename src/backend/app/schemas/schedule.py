from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.shared import SuccessResponse


class ScheduleTask(BaseModel):
    """A single task shown on the calendar for a specific day."""
    id: str
    name: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    rated: bool


class ScheduleResponse(BaseModel):
    """Response for GET /schedule"""
    date: str
    tasks: List[ScheduleTask]  # ✅ Fixed: was "task" (singular)


class BatchScheduleResponse(BaseModel):
    """Response for POST /schedule/batch"""
    success: bool
    scheduled_count: int
    unscheduled_remaining: List[str]
    message: str
    provisional_changes: List[dict]
    execution_time_ms: int


# ---------------------------------------------------------
# Provisional Schemas (Added)
# ---------------------------------------------------------

class ProvisionalChange(BaseModel):
    """A single pending change in the schedule."""
    id: str
    task_id: str
    task_name: str
    change_type: str  # 'insert' or 'move'
    new_slot_start: datetime
    new_slot_end: datetime
    location: Optional[str] = None
    value: float
    fixed: bool


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
