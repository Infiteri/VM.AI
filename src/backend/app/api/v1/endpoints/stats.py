from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.schemas.stats import RateRequest, RateResponse

router = APIRouter()


@router.post("/{id}/rate", status_code=status.HTTP_200_OK, response_model=RateResponse)
def rate_task(
    id: UUID,
    body: RateRequest,
    db: Session = Depends(get_db),
):

    # === TEMPORARY STUB ===
    # Future logic:
    # Fetch task: task = db.query(Task).filter(Task.id == id).first()
    # Validate: if not task → raise 404
    # Call service: stats_recorder.record_completion(task, rating_data)
    # Return response
    # === END STUB ===

    return RateResponse(
        success=True,
        task_id=id,
        stats_updated=True,
        message="Task rated successfully (stub)",
    )
