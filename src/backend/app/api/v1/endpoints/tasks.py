from fastapi import APIRouter, Depends, Query, status, Path, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import setup_logging
from app.schemas.task import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskDetailResponse,
    TaskPayload,
    ParseAddRequest,
    ParseModifyRequest,
    ParseAddResponse,
    ParseModifyResponse,
    UnscheduledResponse,
)
from app.services.task_matcher import task_matcher
from app.services.enrichment import enrichment_service
from app.utils.task_saver import save_commited_task

router = APIRouter()
logger = setup_logging()


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
        draft_id=UUID("00000000-0000-0000-0000-000000000000"),  # Stub UUID
        task=TaskPayload(
            name="Example Task",
            start=datetime(2026, 4, 14, 9, 0),
            deadline=datetime(2026, 4, 15, 17, 0),
            difficulty=0.5,
            duration=60,
            category=["study"],
            location="Home",
            importance=0.5,
            fixed_time=False,
            fixed_start=None,
        ),
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
        task=TaskPayload(
            name="Modified Task",
            start=datetime(2026, 4, 19, 9, 0),
            deadline=datetime(2026, 4, 20, 17, 0),
            difficulty=0.5,
            duration=60,
            category=["study"],
            location="Home",
            importance=0.5,
            fixed_time=False,
            fixed_start=None,
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

    Flow:
        If draft_id is present:
            1. Fetch draft from DB.
            2. Update draft data with body.task edits.
            3. Save to main DB, delete draft.
        Else (Manual Creation):
            1. Run Task Matching & Enrichment pipeline on body.task.
            2. Save to main DB (TODO: implement later).
    """
    if body.draft_id:
        # TODO: Handle draft commit later
        pass
    else:
        match_result = task_matcher.find_match(db, body.task.name)
        enriched = enrichment_service.commit_manual(db, body.task, match_result)

    saved = save_commited_task(db, enriched)

    if not saved:
        raise HTTPException(
            status_code=500,
            detail="Failed to save task to database"
        )

    return TaskResponse(
        success=True,
        task_id=saved.id,
        status="unscheduled",
        message="Task enrichment complete - saved to DB",
    )


@router.post("/{id}/update", response_model=TaskResponse)
def update_task(
    body: TaskUpdateRequest,
    db: Session = Depends(get_db),
    id: UUID = Path(..., description="ID of the task to update"),
    source: str = Query(..., description="main_schedule | unscheduled | provisional"),
):
    """
    POST /tasks/{id}/update
    Updates an existing task based on its source.
    """
    return TaskResponse(
        success=True,
        task_id=id,
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
# 3. Task Fetching Endpoint
# ---------------------------------------------------------


@router.get("/{id}", response_model=TaskDetailResponse)
def get_task(
    id: UUID,
    db: Session = Depends(get_db),
):
    """ 
    GET /tasks/{id}
    Fetches details of a specific task by ID.
    """
    # TODO: Implement DB query

    return TaskDetailResponse(
        task_id=id,
        task=TaskPayload(
            name="Stub Task for Display",
            start=datetime(2026, 4, 19, 9, 0),
            deadline=datetime(2026, 4, 20, 17, 0),
            difficulty=0.5,
            duration=60,
            category=["study"],
            location="Home",
            importance=0.5,
            fixed_time=False,
            fixed_start=None,
        ),
        created_at=datetime(2026, 4, 10, 12, 0),
    )


# ---------------------------------------------------------
# 4. Queue Endpoint
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
