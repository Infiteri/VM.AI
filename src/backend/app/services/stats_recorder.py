import copy
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Task, TaskStatistics, CategoryStatistics
from app.models.statistics import (
    TaskStatisticsLocation,
    CategoryStatisticsLocation,
)
from app.models import Location
from app.core.logging_config import setup_logging

logger = setup_logging()

RECORDS_NR_TRACK = 30


class StatsRecorder:
    """
    Service for recording task statistics after commit.
    
    Updates:
    - TaskStatistics (avg_difficulty, avg_duration, records)
    - TaskStatisticsLocation (count per location)
    - CategoryStatistics for each category
    - CategoryStatisticsLocation (count per location)
    """

    RECORDS_NR_TRACK = RECORDS_NR_TRACK

    def update_stats_after_commit(self, db: Session, task_uuid: UUID) -> bool:
        """
        Update statistics after a task is committed.
        
        Args:
            db: Database session
            task_uuid: UUID of the committed task
            
        Returns:
            bool: True if successful, False on error
        """
        try:
            # Fetch task from DB
            task = db.query(Task).filter(Task.id == task_uuid).first()
            if not task:
                logger.error(f"Task not found: {task_uuid}")
                return False

            # Update TaskStatistics
            self._update_task_statistics(db, task)

            # Update TaskStatisticsLocation
            self._update_task_statistics_location(db, task)

            # Update CategoryStatistics for each category
            self._update_category_statistics(db, task)

            # Update CategoryStatisticsLocation
            self._update_category_statistics_location(db, task)

            db.commit()
            logger.info(f"Stats updated for task: {task.name}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update stats for task {task_uuid}: {e}")
            return False

    def _update_task_statistics(self, db: Session, task: Task) -> None:
        """Update TaskStatistics with new task data."""
        stats = db.query(TaskStatistics).filter(
            TaskStatistics.id == task.task_statistics_id
        ).first()

        if not stats:
            logger.warning(f"TaskStatistics not found for task: {task.name}")
            return

        # Get current values
        current_records = stats.records or 0
        current_difficulty = stats.avg_difficulty or 0.0

        # Update avg_difficulty: round((avg * records + new) / (records + 1), 2)
        new_difficulty = round(
            (current_difficulty * current_records + task.difficulty) / (current_records + 1),
            2
        )
        stats.avg_difficulty = new_difficulty

        # Update duration bucket
        bucket = self._get_duration_bucket(task.difficulty)
        avg_duration = copy.deepcopy(stats.avg_duration) if stats.avg_duration else {}

        if bucket not in avg_duration:
            avg_duration[bucket] = {"count": 0, "avg": 0}

        current_count = avg_duration[bucket].get("count", 0)
        current_avg = avg_duration[bucket].get("avg", 0)

        # Handle RECORDS_NR_TRACK limit: if at limit, calculate effect of oldest record
        if current_records >= self.RECORDS_NR_TRACK:
            # Estimate: remove oldest record contribution (assume average)
            # New avg = (current_avg * count - avg_removed) / (count - 1)
            # For simplicity, we just add new and keep tracking
            pass

        # Update bucket
        new_avg_duration = round(
            (current_avg * current_count + task.duration) / (current_count + 1),
            2
        )
        avg_duration[bucket] = {
            "count": current_count + 1,
            "avg": new_avg_duration
        }
        stats.avg_duration = avg_duration

        # Increment records
        stats.records = current_records + 1

        logger.info(f"[STATS] Final: {stats}")

    def _update_task_statistics_location(self, db: Session, task: Task) -> None:
        """Update TaskStatisticsLocation count for task's location."""
        stats = db.query(TaskStatistics).filter(
            TaskStatistics.id == task.task_statistics_id
        ).first()

        if not stats:
            return

        # Find or create location record
        loc_record = db.query(TaskStatisticsLocation).filter(
            TaskStatisticsLocation.statistics_id == stats.id,
            TaskStatisticsLocation.location_id == task.location_id,
        ).first()

        if loc_record:
            loc_record.count += 1
        else:
            loc_record = TaskStatisticsLocation(
                statistics_id=stats.id,
                location_id=task.location_id,
                count=1,
            )
            db.add(loc_record)

        logger.info(f"Updated TaskStatisticsLocation for: {task.name}")

    def _update_category_statistics(self, db: Session, task: Task) -> None:
        """Update CategoryStatistics for each category of the task."""
        # Get task categories
        from app.models import TaskCategory

        task_categories = db.query(TaskCategory).filter(
            TaskCategory.task_id == task.id
        ).all()

        for tc in task_categories:
            # Get category statistics
            cat_stats = db.query(CategoryStatistics).filter(
                CategoryStatistics.category_id == tc.category_id
            ).first()

            if not cat_stats:
                logger.warning(f"CategoryStatistics not found for category_id: {tc.category_id}")
                continue

            # Get current values
            current_records = cat_stats.records or 0
            current_difficulty = cat_stats.avg_difficulty or 0.0

            # Update avg_difficulty
            new_difficulty = round(
                (current_difficulty * current_records + task.difficulty) / (current_records + 1),
                2
            )
            cat_stats.avg_difficulty = new_difficulty

            # Update duration bucket
            bucket = self._get_duration_bucket(task.difficulty)
            avg_duration = copy.deepcopy(cat_stats.avg_duration) if cat_stats.avg_duration else {}

            if bucket not in avg_duration:
                avg_duration[bucket] = {"count": 0, "avg": 0}

            current_count = avg_duration[bucket].get("count", 0)
            current_avg = avg_duration[bucket].get("avg", 0)

            new_avg_duration = round(
                (current_avg * current_count + task.duration) / (current_count + 1),
                2
            )
            avg_duration[bucket] = {
                "count": current_count + 1,
                "avg": new_avg_duration
            }
            cat_stats.avg_duration = avg_duration

            # Increment records
            cat_stats.records = current_records + 1

            logger.info(f"[CAT_STATS] Final: {cat_stats}")

    def _update_category_statistics_location(self, db: Session, task: Task) -> None:
        """Update CategoryStatisticsLocation for each category of the task."""
        from app.models import TaskCategory, CategoryStatistics

        task_categories = db.query(TaskCategory).filter(
            TaskCategory.task_id == task.id
        ).all()

        for tc in task_categories:
            # Get category statistics
            cat_stats = db.query(CategoryStatistics).filter(
                CategoryStatistics.category_id == tc.category_id
            ).first()

            if not cat_stats:
                continue

            # Find or create location record
            loc_record = db.query(CategoryStatisticsLocation).filter(
                CategoryStatisticsLocation.statistics_id == cat_stats.id,
                CategoryStatisticsLocation.location_id == task.location_id,
            ).first()

            if loc_record:
                loc_record.count += 1
            else:
                loc_record = CategoryStatisticsLocation(
                    statistics_id=cat_stats.id,
                    location_id=task.location_id,
                    count=1,
                )
                db.add(loc_record)

        logger.info(f"Updated CategoryStatisticsLocation for task: {task.name}")

    def _get_duration_bucket(self, difficulty: float) -> str:
        """Calculate duration bucket: round(difficulty * 2) / 2"""
        return str(round(difficulty * 2) / 2)


stats_recorder = StatsRecorder()