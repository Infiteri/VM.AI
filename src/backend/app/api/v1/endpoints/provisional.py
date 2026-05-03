from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import time

from app.core.database import get_db
from app.models.schedule import ProvisionalSlot, MainScheduleSlot
from app.models.task import Task
from app.models.workflow import ScheduleChange
from app.schemas.schedule import (
    ProvisionalChangesResponse,
    ProvisionalResetResponse,
    ProvisionalCommitResponse
)

router = APIRouter()


@router.get("/changes", response_model=ProvisionalChangesResponse)
def get_provisional_changes(
    db: Session = Depends(get_db),
):
    """
    GET /provisional/changes

    Fetches all pending inserts/moves in the working schedule.
    """
    slots = db.query(ProvisionalSlot).join(Task).all()

    changes = []
    for slot in slots:
        task = slot.task

        change = db.query(ScheduleChange).filter(
            ScheduleChange.provisional_schedule_slot_id == slot.id
        ).first()

        location_name = task.location.name if task.location else ""

        changes.append({
            "provisional_schedule_slot_id": slot.id,
            "task_id": task.id,
            "task_name": task.name,
            "change_type": change.change_type,
            "new_slot_start": slot.start,
            "new_slot_end": slot.end,
            "location": location_name,
        })

    return ProvisionalChangesResponse(
        changes=changes,
        total_count=len(changes),
    )


@router.post("/reset", status_code=status.HTTP_200_OK, response_model=ProvisionalResetResponse)
def reset_provisional(
    db: Session = Depends(get_db),
):
    """
    POST /provisional/reset

    Discards all provisional changes and resets working copy
    to match committed schedule.
    """
    changes_discarded = db.query(ScheduleChange).count()

    db.query(ProvisionalSlot).delete(synchronize_session=False)

    main_slots = db.query(MainScheduleSlot).all()
    for slot in main_slots:
        new_slot = ProvisionalSlot(
            task_id=slot.task_id,
            start=slot.start,
            end=slot.end,
            value=slot.value,
            fixed=slot.fixed,
            location=slot.location,
        )
        db.add(new_slot)

    db.commit()

    return ProvisionalResetResponse(
        success=True,
        message="Provisional schedule reset to main schedule",
        changes_discarded=changes_discarded,
    )


@router.post("/commit", status_code=status.HTTP_200_OK, response_model=ProvisionalCommitResponse)
def commit_provisional(
    db: Session = Depends(get_db),
):
    """
    POST /provisional/commit

    Atomically copies provisional_schedule to main_schedule
    and clears change logs.
    """
    start = time.time()
    
    committed_count = db.query(ScheduleChange).count()
    
    db.query(MainScheduleSlot).delete(synchronize_session=False)
    
    provisional_slots = db.query(ProvisionalSlot).all()
    for slot in provisional_slots:
        new_slot = MainScheduleSlot(
            task_id=slot.task_id,
            start=slot.start,
            end=slot.end,
            value=slot.value,
            fixed=slot.fixed,
            location=slot.location,
        )
        db.add(new_slot)
    
    db.query(ScheduleChange).delete(synchronize_session=False)
    
    db.commit()
    
    transaction_time_ms = int((time.time() - start) * 1000)
    
    return ProvisionalCommitResponse(
        success=True,
        committed_count=committed_count,
        transaction_time_ms=transaction_time_ms,
        message="Schedule committed successfully",
    )
