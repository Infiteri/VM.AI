from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime
from app.schemas.shared import SuccessResponse


class TaskField(BaseModel):
    """
    Represents a single field in a task request.
    Example: { "value": "Homework", "predicted": false }
    """
    value: Union[str, int, float, bool, None]  # Can be any type
    predicted: bool


class TaskPayload(BaseModel):
    """
    The nested object inside TaskCreateRequest.
    Defines exactly what fields a task must have.
    """
    name: TaskField
    deadline: TaskField
    difficulty: TaskField
    duration: TaskField
    category: TaskField
    location: TaskField
    fixed_time: TaskField
    importance: TaskField


class TaskCreateRequest(BaseModel):
    """
    The full JSON body sent by frontend to create a task.
    """
    task: TaskPayload  # ✅ Strict validation instead of "dict"


class TaskResponse(SuccessResponse):
    """
    What the backend returns after creating a task.
    Inherits 'success' from SuccessResponse.
    """
    task_id: str
    status: str = "unscheduled"
