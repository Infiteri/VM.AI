import logging
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Task, Location, Category, TaskCategory, TaskStatistics
from app.schemas.enrichment import TaskPayloadComputedWithRefs

logger = logging.getLogger(__name__)


def save_commited_task(db: Session, enriched_task: TaskPayloadComputedWithRefs) -> Task | None:
    """
    Save enriched task to DB tables using ORM.
    
    Returns True on success, False on failure (with rollback).
    """
    try:
        location = _ensure_location(db, enriched_task.location)
        
        task_stats_ids = _handle_task_statistics(db, enriched_task)
        
        task = Task(
            task_statistics_id=task_stats_ids[0],
            associated_task_statistics_id=task_stats_ids[1],
            name=enriched_task.name,
            start=enriched_task.start,
            deadline=enriched_task.deadline,
            difficulty=enriched_task.difficulty,
            duration=enriched_task.duration,
            location_id=location.id,
            importance=enriched_task.importance,
            urgency=enriched_task.urgency,
            value=enriched_task.value,
            fixed_time=enriched_task.fixed_time,
            fixed_start=enriched_task.fixed_start,
            rated=False,
        )
        db.add(task)
        db.flush()
        
        for priority, cat_name in enumerate(enriched_task.category):
            category = _ensure_category(db, cat_name)
            db.add(TaskCategory(
                task_id=task.id,
                category_id=category.id,
                priority=priority
            ))
        
        db.commit()
        logger.info(f"Task saved successfully: {enriched_task.name}")
        return task
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save task '{enriched_task.name}': {e}")
        return None


def _ensure_location(db: Session, location_name: str) -> Location:
    """Ensure location exists in DB, create if needed. Returns Location object."""
    location = db.query(Location).filter(Location.name == location_name).first()
    
    if not location:
        location = Location(name=location_name)
        db.add(location)
        db.flush()
        logger.info(f"Created new location: {location_name}")
    
    return location


def _ensure_category(db: Session, category_name: str) -> Category:
    """Ensure category exists in DB, create if needed. Returns Category object."""
    category = db.query(Category).filter(Category.name == category_name).first()
    
    if not category:
        category = Category(name=category_name)
        db.add(category)
        db.flush()
        logger.info(f"Created new category: {category_name}")
    
    return category


def _handle_task_statistics(
    db: Session,
    enriched_task: TaskPayloadComputedWithRefs
) -> Tuple[UUID, Optional[UUID]]:
    """
    Handle task_statistics based on association_status.
    
    Returns (task_statistics_id, associated_task_statistics_id) for Task table.
    
    Logic from notes.log:
    - "same": task_statistics_id = associated_id, associated_task_statistics_id = None
    - "similar": task_statistics_id = new row's id, associated_task_statistics_id = associated_id
    - "none": task_statistics_id = new row's id, associated_task_statistics_id = None
    """
    association_status = enriched_task.association_status
    associated_id = enriched_task.task_statistics_id
    
    if association_status == "same" and associated_id:
        return (associated_id, None)
    
    new_stats = _create_task_statistics(
        db,
        enriched_task.name,
        enriched_task.name_vector
    )
    
    if association_status == "similar" and associated_id:
        return (new_stats.id, associated_id)
    
    return (new_stats.id, None)


def _create_task_statistics(
    db: Session,
    task_name: str,
    name_vector: Optional[List[float]] = None
) -> TaskStatistics:
    """Create new TaskStatistics record. Returns TaskStatistics object."""
    stats = TaskStatistics(
        task_name=task_name,
        task_name_vector=name_vector,
        avg_duration={},
        avg_duration_delta={},
        avg_difficulty=0.0,
        avg_difficulty_delta=0.0,
        completed_count=0,
        uncompleted_count=0,
        records=0,
        task_time_scores={},
    )
    db.add(stats)
    db.flush()
    logger.info(f"Created new task_statistics: {task_name}")
    return stats