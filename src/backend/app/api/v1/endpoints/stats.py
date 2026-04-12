from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db

router = APIRouter()


@router.post("/{id}/rate", status_code=status.HTTP_200_OK)
def rate_task(
    id: UUID,
    db: Session = Depends(get_db),
):
    
    # === TEMPORARY STUB ===
    # Future logic:
    # Fetch task: task = db.query(Task).filter(Task.id == id).first()
    # Validate: if not task → raise 404
    # Call service: stats_recorder.record_completion(task, rating_data)
    # Return response
    # === END STUB ===

    return {
        "success": True,
        "task_id": str(id),
        "stats_updated": True,
        "message": "Task rated successfully (stub)",
    }