from pydantic import BaseModel, model_validator
from typing import Optional, Union, List
from uuid import UUID
from app.schemas.shared import SuccessResponse


# 1. The building block for every field
class TaskField(BaseModel):
    """
    Represents a single field in a task request.
    Now supports Lists for categories!
    """
    value: Union[str, int, float, bool, List[str], None]
    predicted: bool


# 2. The input structure for creating/updating tasks
class TaskPayload(BaseModel):
    """
    The specific fields a task must have.
    Includes validation logic for fixed_time vs start/deadline.
    """
    name: TaskField
    start: TaskField
    deadline: TaskField
    difficulty: TaskField
    duration: TaskField
    category: TaskField
    location: TaskField
    importance: TaskField
    fixed_time: TaskField
    fixed_start: TaskField

    @model_validator(mode="after")
    def check_fixed_time_logic(self):
        """
        Validates that the task is either a 'Fixed' task OR a 'Flexible' task,
        but not a mix of both.
        """
        is_fixed = self.fixed_time.value
        has_fixed_start = self.fixed_start.value is not None
        has_start = self.start.value is not None
        has_deadline = self.deadline.value is not None

        # CASE 1: FIXED TIME TASK
        if is_fixed:
            if not has_fixed_start:
                raise ValueError("For fixed tasks, 'fixed_start' must be provided.")
            if has_start or has_deadline:
                raise ValueError("For fixed tasks, 'start' and 'deadline' must be null.")
        
        # CASE 2: FLEXIBLE (NORMAL) TASK
        else:
            if has_fixed_start:
                raise ValueError("For flexible tasks, 'fixed_start' must be null.")
            if not has_start or not has_deadline:
                raise ValueError("For flexible tasks, BOTH 'start' and 'deadline' must be provided.")

        return self


# 3. Request Wrappers
class TaskCreateRequest(BaseModel):
    """Input for POST /tasks"""
    task: TaskPayload

class ParseAddRequest(BaseModel):
    """Input for POST /tasks/parse/add"""
    prompt: str

class ParseModifyRequest(BaseModel):
    """Input for POST /tasks/parse/modify"""
    task_id: UUID
    prompt: str


# 4. Response Wrappers
class TaskResponse(SuccessResponse):
    """Response for POST /tasks and POST /tasks/{id}/update"""
    task_id: str
    status: str = "unscheduled"

class ParseAddResponse(BaseModel):
    """Response for POST /tasks/parse/add"""
    enriched_task: TaskPayload

class ParseModifyResponse(BaseModel):
    """Response for POST /tasks/parse/modify"""
    task_id: str
    enriched_task: TaskPayload


# 5. Unscheduled Queue Schemas
class UnscheduledTaskItem(BaseModel):
    """A single task in the unscheduled queue."""
    id: str
    name: str
    duration: int
    deadline: str
    difficulty: float
    location: Optional[str] = None
    category: List[str]
    fixed_time: bool
    fixed_start: Optional[str] = None
    importance: float
    urgency: float
    value: float
    created_at: str

class UnscheduledResponse(BaseModel):
    """Response for GET /tasks/unscheduled"""
    tasks: List[UnscheduledTaskItem]
    total_count: int
