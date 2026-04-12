from fastapi import APIRouter, Depends, Query, status, Path
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db

router = APIRouter()


# ---------------------------------------------------------
# 1. NLP Parsing Endpoints
# ---------------------------------------------------------

@router.post("/parse/add")
def parse_add_task(
    prompt: str,
    db: Session = Depends(get_db),
):
    """
    POST /tasks/parse/add
    Parses natural language input to extract task fields.
    """
    # TODO: Call NLP Parser Service
    return {
        "enriched_task": {
            "name": {"value": "Example Task", "predicted": False},
            "deadline": {"value": "2026-04-15T00:00:00", "predicted": True},
        },
        "message": "Parsed successfully (stub)",
    }


@router.post("/parse/modify")
def parse_modify_task(
    task_id: UUID,
    prompt: str,
    db: Session = Depends(get_db),
):
    """
    POST /tasks/parse/modify
    Parses modification prompts.
    """
    # TODO: Call NLP Parser Service
    return {
        "task_id": str(task_id),
        "enriched_task": {"name": {"value": "Modified Task", "predicted": True}},
        "message": "Modification parsed successfully (stub)",
    }


# ---------------------------------------------------------
# 2. Task CRUD Endpoints
# ---------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_task(
    db: Session = Depends(get_db),
):
    """
    POST /tasks
    Creates a new task in the database.
    """
    # TODO: Wire to Task Matching -> Enrichment -> DB
    return {
        "success": True,
        "task_id": "550e8400-e29b-41d4-a716-446655440001",
        "status": "unscheduled",
        "message": "Task created successfully (stub)",
    }


@router.post("/{id}/update")
def update_task(
    id: UUID = Path(..., description="ID of the task to update"),
    source: str = Query(..., description="main_schedule | unscheduled | provisional"),
    db: Session = Depends(get_db),
):
    """
    POST /tasks/{id}/update
    Updates an existing task based on its source.
    """
    # TODO: Implement logic to pull old task and create new version
    return {
        "success": True,
        "new_task_id": "new-uuid-here",
        "old_task_id": str(id),
        "message": "Task updated successfully (stub)",
    }


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id: UUID = Path(..., description="ID of the task to delete"),
    source: str = Query(..., description="main_schedule | unscheduled | provisional"),
    db: Session = Depends(get_db),
):
    """
    DELETE /tasks/{id}
    Deletes a task based on its source context.
    """
    # TODO: Implement cascading delete logic
    # Note: 204 No Content means success with no response body
    pass


# ---------------------------------------------------------
# 3. Queue Endpoint
# ---------------------------------------------------------

@router.get("/unscheduled")
def get_unscheduled(
    limit: int = Query(50, description="Max number of tasks to return"),
    db: Session = Depends(get_db),
):
    """
    GET /tasks/unscheduled
    Fetches the queue of tasks waiting for scheduling.
    """
    # TODO: Query unscheduled Tasks with FIFO ordering
    return {
        "tasks": [],
        "total_count": 0,
    }
