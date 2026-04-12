from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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

    TODO: Query provisional_schedule + schedule_changes
    For now, returns empty stub.
    """
    # === TEMPORARY STUB ===
    return ProvisionalChangesResponse(
        changes=[],
        total_count=0,
    )


@router.post("/reset", status_code=status.HTTP_200_OK, response_model=ProvisionalResetResponse)
def reset_provisional(
    db: Session = Depends(get_db),
):
    """
    POST /provisional/reset
    
    Discards all provisional changes and resets working copy 
    to match committed schedule.
    
    TODO: Truncate provisional_schedule and schedule_changes, 
    then copy from main_schedule.
    For now, returns success stub.
    """
    # === TEMPORARY STUB ===
    return ProvisionalResetResponse(
        success=True,
        message="Provisional schedule reset to main schedule (stub)",
        changes_discarded=0,
    )


@router.post("/commit", status_code=status.HTTP_200_OK, response_model=ProvisionalCommitResponse)
def commit_provisional(
    db: Session = Depends(get_db),
):
    """
    POST /provisional/commit
    
    Atomically copies provisional_schedule to main_schedule 
    and clears change logs.
    
    TODO: Wrap in a single PostgreSQL transaction:
          1. DELETE FROM main_schedule
          2. INSERT INTO main_schedule SELECT * FROM provisional_schedule
          3. TRUNCATE schedule_changes
    For now, returns success stub.
    """
    # === TEMPORARY STUB ===
    return ProvisionalCommitResponse(
        success=True,
        committed_count=0,
        message="Schedule committed successfully (stub)",
        transaction_time_ms=0,
    )
