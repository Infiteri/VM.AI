from pydantic import BaseModel
from typing import Optional
from app.schemas.shared import SuccessResponse

class RateRequest(BaseModel):
    completed: bool
    actual_duration: Optional[int] = None
    actual_difficulty: Optional[float] = None

class RateResponse(SuccessResponse):
    task_id: str
    stats_updated: bool