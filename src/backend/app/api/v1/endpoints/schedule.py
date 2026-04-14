from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, date

from app.core.database import get_db
from app.schemas.schedule import ScheduleResponse, BatchScheduleResponse

router = APIRouter()


@router.get("/", response_model=ScheduleResponse)
def get_schedule(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
):
    """
    GET /schedule?date=YYYY-MM-DD
    """
    # Stub Response
    return ScheduleResponse(
        date=date,
        tasks=[],
    )


@router.post("/batch", status_code=status.HTTP_200_OK, response_model=BatchScheduleResponse)
def schedule_batch(
    db: Session = Depends(get_db),
):
    """
    POST /schedule/batch
    """
    # Stub Response
    return BatchScheduleResponse(
        success=True,
        scheduled_count=0,
        unscheduled_remaining=[],  # List of TaskDetailResponse
        message="All tasks scheduled successfully (stub)",
        provisional_changes=[],
        execution_time_ms=0,
    )