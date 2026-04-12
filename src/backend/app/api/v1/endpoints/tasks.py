from fastapi import APIRouter, Depends, Query, status, Path
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.schemas.task import (
    TaskCreateRequest, 
    TaskResponse, 
    ParseAddRequest, 
    ParseModifyRequest,
    ParseAddResponse,
    ParseModifyResponse,
    UnscheduledResponse,
    TaskPayload,
    TaskField
)

router = APIRouter()


# ---------------------------------------------------------
# 1. NLP Parsing Endpoints
# ---------------------------------------------------------

@router.post("/parse/add", response_model=ParseAddResponse)
def parse_add_task(
    body: ParseAddRequest,
    db: Session = Depends(get_db),
):
    """
    POST /tasks/parse/add
    Parses natural language input to extract task fields.
    """
    # TODO: Call NLP Parser Service
    
    return ParseAddResponse(
        enriched_task=TaskPayload(
            name=TaskField(value="Example Task", predicted=False),
            start=TaskField(value="2026-04-12T00:00:00", predicted=False),
            deadline=TaskField(value="2026-04-15T00:00:00", predicted=True),
            difficulty=TaskField(value=0.5, predicted=True),
            duration=TaskField(value=60, predicted=True),
            category=TaskField(value=["study"], predicted=True),
            location=TaskField(value="Home", predicted=True),
            importance=TaskField(value=0.5, predicted=True),
            fixed_time=TaskField(value=False, predicted=False),
            fixed_start=TaskField(value=None, predicted=False),
        )
    )


@router.post("/parse/modify", response_model=ParseModifyResponse)
def parse_modify_task(
    body: ParseModifyRequest,
    db: Session = Depends(get_db),
):
    """
    POST /tasks/parse/modify
    Parses modification prompts.
    """
    # TODO: Call NLP Parser Service
    
    return ParseModifyResponse(
        task_id=str(body.task_id),
        enriched_task=TaskPayload(
            name=TaskField(value="Modified Task", predicted=True),
            start=TaskField(value="2026-04-10T00:00:00", predicted=False),
            deadline=TaskField(value="2026-04-20T00:00:00", predicted=True),
            difficulty=TaskField(value=0.5, predicted=True),
            duration=TaskField(value=60, predicted=True),
            category=TaskField(value=["study"], predicted=True),
            location=TaskField(value="Home", predicted=True),
            importance=TaskField(value=0.5, predicted=True),
            fixed_time=TaskField(value=False, predicted=False),
            fixed_start=TaskField(value=None, predicted=False),
        ),
    )


# ---------------------------------------------------------
# 2. Task CRUD Endpoints
# ---------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TaskResponse)
def create_task(
    body: TaskCreateRequest,
    db: Session = Depends(get_db),
):
    """
    POST /tasks
    Creates a new task in the database.
    """
    # TODO: Wire to Task Matching -> Enrichment -> DB
    
    return TaskResponse(
        success=True,
        task_id="550e8400-e29b-41d4-a716-446655440001",
        status="unscheduled",
        message="Task created successfully (stub)",
    )


@router.post("/{id}/update", response_model=TaskResponse)
def update_task(
    id: UUID = Path(..., description="ID of the task to update"),
    source: str = Query(..., description="main_schedule | unscheduled | provisional"),
    body: TaskCreateRequest = None, 
    db: Session = Depends(get_db),
):
    """
    POST /tasks/{id}/update
    Updates an existing task based on its source.
    """
    return TaskResponse(
        success=True,
        task_id="new-uuid-here",
        status="unscheduled",
        message="Task updated successfully (stub)",
    )


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
    pass


# ---------------------------------------------------------
# 3. Queue Endpoint
# ---------------------------------------------------------

@router.get("/unscheduled", response_model=UnscheduledResponse)
def get_unscheduled(
    limit: int = Query(50, description="Max number of tasks to return"),
    db: Session = Depends(get_db),
):
    """
    GET /tasks/unscheduled
    Fetches the queue of tasks waiting for scheduling.
    """
    return UnscheduledResponse(
        tasks=[],
        total_count=0,
    )
