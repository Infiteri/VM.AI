from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db

router = APIRouter()

@router.get("/")
def get_schedule(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
):
    # === TEMPORARY STUB ===
    # Future logic:
    # 1. Validate date format: parse date string
    # 2. Query: slots = db.query(MainScheduleSlot).filter(
    #        func.date(MainScheduleSlot.start) == parsed_date
    #    ).all()
    # 3. Build response with task details
    # === END STUB ===
    
    return {
        "date": date,
        "tasks": [],  # Empty for now
    }

@router.post("/batch", status_code=status.HTTP_200_OK)
def schedule_batch(
    db: Session = Depends(get_db),
):
    # === TEMPORARY STUB ===
    # Future logic:
    # 1. Fetch unscheduled task IDs from DB
    # 2. Call scheduler engine: result = scheduler.run(task_ids, db)
    # 3. Write results to provisional_schedule
    # 4. Log to schedule_changes
    # 5. Remove from unscheduled_tasks
    # 6. Return response with scheduled_count and execution_time_ms
    # === END STUB ===
    
    return {
        "success": True,
        "scheduled_count": 0,
        "unscheduled_remaining": [],
        "message": "All tasks scheduled successfully (stub)",
        "provisional_changes": [],
        "execution_time_ms": 0,
    }