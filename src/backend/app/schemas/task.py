from pydantic import BaseModel, model_validator, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.schemas.shared import SuccessResponse


# 1. The input structure for creating/updating tasks
class TaskPayload(BaseModel):
    """
    Clean task data with strict validation constraints.
    """
    name: str = Field(..., min_length=1, description="Task name cannot be empty")
    
    start: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    difficulty: float = Field(..., gt=0.0, le=1.0, description="Must be between 0.0 and 1.0")
    duration: int = Field(..., gt=0, lt=1440, description="Must be positive minutes < 1440")
    
    category: List[str] = Field(..., min_length=1, description="At least one category required")
    location: str  # Not optional
    
    importance: float = Field(..., gt=0.0, le=1.0, description="Must be between 0.0 and 1.0")
    
    fixed_time: bool = False
    fixed_start: Optional[datetime] = None

    @model_validator(mode='after')
    def check_fixed_logic(self):
        """
        Validates the relationship between fixed_time and temporal fields.
        """
        if self.fixed_time:
            if self.start is not None or self.deadline is not None:
                raise ValueError("If fixed_time is true, start and deadline must be null.")
            if self.fixed_start is None:
                raise ValueError("If fixed_time is true, fixed_start is required.")
        else:
            if self.start is None or self.deadline is None:
                raise ValueError("If fixed_time is false, start and deadline are required.")
            if self.fixed_start is not None:
                raise ValueError("If fixed_time is false, fixed_start must be null.")
        return self


# 2. Request Wrappers
class TaskCreateRequest(BaseModel):
    """Input for POST /tasks (Commit Phase)"""
    draft_id: Optional[UUID] = None  # Optional: Only required if committing from Chat/AI
    task: TaskPayload

class TaskUpdateRequest(BaseModel):
    """Input for POST /tasks/{id}/update"""
    task: TaskPayload

class ParseAddRequest(BaseModel):
    """Input for POST /tasks/parse/add"""
    prompt: str

class ParseModifyRequest(BaseModel):
    """Input for POST /tasks/parse/modify"""
    task_id: UUID
    prompt: str


# 3. Response Wrappers
class TaskResponse(SuccessResponse):
    """Response for POST /tasks and POST /tasks/{id}/update"""
    task_id: UUID
    status: str = "unscheduled"

class ParseAddResponse(BaseModel):
    """Response for POST /tasks/parse/add"""
    draft_id: UUID 
    task: TaskPayload

class ParseModifyResponse(BaseModel):
    """Response for POST /tasks/parse/modify"""
    task_id: UUID
    task: TaskPayload


# 4. Task Detail (Read Model)
class TaskDetailResponse(BaseModel):
    """Detailed task data returned when fetching a single task or in queues."""
    task_id: UUID
    payload: TaskPayload
    created_at: datetime


# 5. Unscheduled Queue Schema
class UnscheduledResponse(BaseModel):
    """Response for GET /tasks/unscheduled"""
    tasks: List[TaskDetailResponse]
    total_count: int
