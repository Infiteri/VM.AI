from pydantic import BaseModel, model_validator
from typing import Optional, Union, List
from uuid import UUID
from app.schemas.shared import SuccessResponse


# 1. The input structure for creating/updating tasks
class TaskPayload(BaseModel):
    """
    Clean task data without predicted flags.
    Matches the display fields agreed upon.
    """
    name: str
    start: Optional[str] = None
    deadline: Optional[str] = None
    difficulty: float
    duration: int
    category: List[str]
    location: Optional[str] = None
    importance: float
    fixed_time: bool = False
    fixed_start: Optional[str] = None

    @model_validator(mode="after")
    def check_fixed_time_logic(self):
        """
        Validates that the task is either a 'Fixed' task OR a 'Flexible' task.
        """
        # Flexible Task: Must have start AND deadline. Fixed fields must be null.
        if not self.fixed_time:
            if self.fixed_start is not None:
                raise ValueError("For flexible tasks, 'fixed_start' must be null.")
            if self.start is None or self.deadline is None:
                raise ValueError("For flexible tasks, BOTH 'start' and 'deadline' must be provided.")
        
        # Fixed Task: Must have fixed_start. Flexible fields must be null.
        else:
            if self.fixed_start is None:
                raise ValueError("For fixed tasks, 'fixed_start' must be provided.")
            if self.start is not None or self.deadline is not None:
                raise ValueError("For fixed tasks, 'start' and 'deadline' must be null.")

        return self


# 2. Request Wrappers
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


# 3. Response Wrappers
class TaskResponse(SuccessResponse):
    """Response for POST /tasks and POST /tasks/{id}/update"""
    task_id: str
    status: str = "unscheduled"

class ParseAddResponse(BaseModel):
    """Response for POST /tasks/parse/add"""
    task: TaskPayload

class ParseModifyResponse(BaseModel):
    """Response for POST /tasks/parse/modify"""
    task_id: str
    task: TaskPayload


# 4. Unscheduled Queue Schemas
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
