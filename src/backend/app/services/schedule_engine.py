"""
Schedule Engine Service
Part of VM.AI pipeline - Stage 4

Handles:
- Constraint solving
- Slot generation
- Scoring
- Displacement handling

Version: 2.0 (Class-based)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from uuid import UUID
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.schedule import ProvisionalSlot, MainScheduleSlot
from app.models.workflow import UnscheduledTask, ScheduleChange
from app.models.statistics import TaskStatistics, CategoryStatistics
from app.models.task_category import TaskCategory
from app.models.category import Category
from app.schemas.schedule import SchedulingResult, BatchSchedulingResult
from app.core.logging_config import setup_logging

logger = setup_logging()


# ============================================================================
# CONSTANTS (class-level)
# ============================================================================

SLOT_INTERVAL_MINUTES = 15
HORIZON_DAYS = 7
TOP_N_CANDIDATES = 400
VALUE_THRESHOLD = 1.25
MAX_DISPLACEMENT_LAYERS = 1
TIMEOUT_SECONDS = 12

LOCATION_BASE_BOOST = 0.25
FREE_SLOT_BOOST = 0.5
TIME_SCORE_AMPLIFIER = 0.3
URGENCY_AMPLIFIER = 0.3
CONTINUITY_BASE_BOOST = 0.1
OVERLAP_BASE_PENALTY = 0.15
BASE_SLOT_SCORE = 1.0

DEAD_ZONES = [
    ("23:00", "06:00"),
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TimeWindow:
    """Represents a continuous time window for scheduling."""
    date: str
    start_time: str
    end_time: str


@dataclass
class CandidateSlot:
    """A candidate slot with score."""
    start: datetime
    end: datetime
    score: float


# ============================================================================
# SCHEDULE ENGINE CLASS
# ============================================================================

class ScheduleEngine:
    """
    Schedule engine service.
    
    Public Methods:
        schedule_single()   - Schedule one task
        schedule_batch() - Schedule multiple tasks
    """
    
    # ============================================================================
    # PUBLIC METHODS
    # ============================================================================
    
    def schedule_single(
        self,
        task: Task,
        db: Session,
    ) -> SchedulingResult:
        """
        Schedule a single task into the provisional schedule.

        Uses savepoint to ensure provisional slot is restored on failure.
        If a task already exists in provisional_schedule, it is deleted
        before scheduling. On failure, the savepoint rollback restores
        the deleted slot.

        Args:
            task: Task to schedule
            db: Database session

        Returns:
            SchedulingResult with success status and slot info.
        """
        logger.info(f"Scheduling task: {task.name} (ID: {task.id})")

        with db.nested():
            try:
                if task.fixed_time:
                    return self._schedule_fixed_task(task, db)
                else:
                    return self._schedule_flexible_task(task, db)
            except Exception as e:
                logger.error(f"Scheduling failed for task {task.id}: {e}")
                return SchedulingResult(
                    success=False,
                    task_id=task.id,
                    slot_id=None,
                    slot_start=None,
                    slot_end=None,
                    displaced_tasks=[],
                    message="Scheduling failed",
                )
    
    
    def schedule_batch(
        self,
        db: Session,
        timeout: int = TIMEOUT_SECONDS,
        task_ids: Optional[List[UUID]] = None,
    ) -> BatchSchedulingResult:
        """
        Schedule tasks from unscheduled_tasks queue or from provided list.

        If task_ids is None: query unscheduled_tasks queue
        If task_ids provided: use provided list

        Args:
            db: Database session
            timeout: Maximum execution time in seconds
            task_ids: Optional list of task IDs to schedule

        Returns:
            BatchSchedulingResult with scheduling results.
        """
        start_time = datetime.utcnow()
        logger.info("Starting batch scheduling")
        
        if task_ids is not None:
            tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
            entries = tasks
            logger.info(f"Scheduling {len(task_ids)} provided task IDs")
        else:
            entries = (
                db.query(UnscheduledTask)
                .join(Task)
                .order_by(UnscheduledTask.created_at)
                .all()
            )
            logger.info(f"Scheduling {len(entries)} tasks from queue")
        
        results: List[Any] = []
        scheduled_count = 0
        failed_count = 0
        unscheduled_remaining: List[UUID] = []

        for entry in entries:
            if isinstance(entry, Task):
                task = entry
            else:
                task = entry.task

            if not task:
                logger.warning(f"Task not found")
                failed_count += 1
                unscheduled_remaining.append(entry.task_id if hasattr(entry, 'task_id') else None)
                continue

            result = self.schedule_single(task, db)
            results.append(result)

            if result.success:
                scheduled_count += 1
                if task_ids is None and hasattr(entry, 'task_id'):
                    db.delete(entry)
                db.commit()
            else:
                failed_count += 1
                unscheduled_remaining.append(task.id)

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                logger.warning(f"Timeout reached after {elapsed:.1f}s")
                break

        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"Batch complete: {scheduled_count} scheduled, {failed_count} failed, "
            f"{execution_time_ms}ms"
        )

        return BatchSchedulingResult(
            scheduled_count=scheduled_count,
            failed_count=failed_count,
            unscheduled_remaining=[uid for uid in unscheduled_remaining if uid is not None],
            results=results,
            execution_time_ms=execution_time_ms,
        )
    
    
    # ============================================================================
    # PRIVATE: FIXED TASK SCHEDULING
    # ============================================================================
    
    def _schedule_fixed_task(
        self,
        task: Task,
        db: Session,
    ) -> SchedulingResult:
        """Schedule a fixed-time task at its fixed_start."""
        if not task.fixed_start or not task.duration:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=None,
                slot_end=None,
                displaced_tasks=[],
                message="Fixed task missing fixed_start or duration",
            )
        
        fixed_start = self._round_down_to_interval(task.fixed_start, SLOT_INTERVAL_MINUTES)
        fixed_end = self._calculate_fixed_task_end(task.fixed_start, task.duration)
        
        logger.debug(f"Fixed task at {fixed_start} - {fixed_end}")
        
        overlapping = self._get_overlapping_tasks(fixed_start, fixed_end, db)
        
        displaced_ids: List[UUID] = []
        
        for existing in overlapping:
            if existing.fixed:
                return SchedulingResult(
                    success=False,
                    task_id=task.id,
                    slot_start=fixed_start,
                    slot_end=fixed_end,
                    displaced_tasks=[],
                    message=f"Slot occupied by fixed task {existing.task_id}",
                )
            
            existing_task = db.query(Task).filter(Task.id == existing.task_id).first()
            if existing_task and existing_task.fixed_time:
                return SchedulingResult(
                    success=False,
                    task_id=task.id,
                    slot_start=fixed_start,
                    slot_end=fixed_end,
                    displaced_tasks=[],
                    message=f"Slot occupied by fixed task {existing.task_id}",
                )
            
            displaced_id = existing.task_id
            
            old_start = existing.start
            old_end = existing.end
            
            db.delete(existing)
            
            existing_task_for_displacement = db.query(Task).filter(Task.id == displaced_id).first()
            if existing_task_for_displacement:
                reschedule_result = self._try_reschedule_task(existing_task_for_displacement, db, layer=1)
                
                if not reschedule_result.success:
                    db.rollback()
                    return SchedulingResult(
                        success=False,
                        task_id=task.id,
                        slot_start=fixed_start,
                        slot_end=fixed_end,
                        displaced_tasks=[],
                        message=f"Cannot displace {displaced_id}: cannot be rescheduled",
                    )
                
                new_change = ScheduleChange(
                    provisional_schedule_slot_id=reschedule_result.slot_id,
                    change_type="move",
                    old_slot_start=old_start,
                    old_slot_end=old_end,
                    new_slot_start=reschedule_result.slot_start,
                    new_slot_end=reschedule_result.slot_end,
                )
                db.add(new_change)
                displaced_ids.append(displaced_id)
            else:
                logger.warning(f"Task {displaced_id} not found for displacement")

        slot = ProvisionalSlot(
            task_id=task.id,
            start=fixed_start,
            end=fixed_end,
            value=task.value,
            fixed=True,
            location=task.location.name if task.location else None,
        )
        db.add(slot)
        db.flush()

        change = ScheduleChange(
            provisional_schedule_slot_id=slot.id,
            change_type="insert",
            new_slot_start=fixed_start,
            new_slot_end=fixed_end,
        )
        db.add(change)
        db.commit()

        logger.info(f"Fixed task scheduled at {fixed_start}")

        return SchedulingResult(
            success=True,
            task_id=task.id,
            slot_id=slot.id,
            slot_start=fixed_start,
            slot_end=fixed_end,
            displaced_tasks=displaced_ids,
            message="Task scheduled at fixed time",
        )
    
    
    # ============================================================================
    # PRIVATE: FLEXIBLE TASK SCHEDULING
    # ============================================================================
    
    def _schedule_flexible_task(
        self,
        task: Task,
        db: Session,
    ) -> SchedulingResult:
        """Schedule a flexible task with full scheduling pipeline."""
        logger.debug(f"Flexible task: {task.name}")
        
        windows = self._get_time_windows(task, db)
        if not windows:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=None,
                slot_end=None,
                displaced_tasks=[],
                message="No viable time windows",
            )
        
        duration = task.duration or 30
        slots = self._generate_slots(windows, duration)
        if not slots:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=None,
                slot_end=None,
                displaced_tasks=[],
                message="No viable slots after generation",
            )
        
        scored_slots = []
        for slot_start in slots:
            slot_end = self._calculate_end(slot_start, duration)
            score = self._score_slot(slot_start, slot_end, task, db)
            scored_slots.append(CandidateSlot(slot_start, slot_end, score))
        
        scored_slots.sort(key=lambda s: s.score, reverse=True)
        top_slots = scored_slots[:TOP_N_CANDIDATES]
        
        if not top_slots:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=None,
                slot_end=None,
                displaced_tasks=[],
                message="No candidate slots after scoring",
            )
        
        for candidate in top_slots:
            result = self._handle_displacement(task, candidate.start, candidate.end, db, layer=1)
            if result.success:
                logger.info(f"Task scheduled at {candidate.start}")
                return result
        
        return SchedulingResult(
            success=False,
            task_id=task.id,
            slot_start=None,
            slot_end=None,
            displaced_tasks=[],
            message="Could not find viable slot",
        )
    
    
    # ============================================================================
    # PRIVATE: RESCHEDULE
    # ============================================================================
    
    def _try_reschedule_task(
        self,
        task: Task,
        db: Session,
        layer: int = 1,
    ) -> SchedulingResult:
        """Try to reschedule a displaced task."""
        if layer > MAX_DISPLACEMENT_LAYERS:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=None,
                slot_end=None,
                displaced_tasks=[],
                message=f"Max displacement layers ({MAX_DISPLACEMENT_LAYERS}) exceeded",
            )
        
        if task.fixed_time:
            return self._schedule_fixed_task(task, db)
        else:
            return self._schedule_flexible_task(task, db)
    
    
    # ============================================================================
    # PRIVATE: CONSTRAINT SOLVER
    # ============================================================================
    
    def _get_time_windows(
        self,
        task: Task,
        db: Session,
    ) -> Dict[str, List[TimeWindow]]:
        """Build viable time windows for task."""
        windows: Dict[str, List[TimeWindow]] = {}
        
        task_start = task.start or datetime.utcnow()
        task_deadline = task.deadline or (task_start + timedelta(days=7))
        
        horizon_end = datetime.utcnow() + timedelta(days=HORIZON_DAYS)
        if task_deadline > horizon_end:
            task_deadline = horizon_end
        
        current = task_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = task_deadline.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            windows[date_str] = [TimeWindow(date=date_str, start_time="00:00", end_time="23:59")]
            current += timedelta(days=1)
        
        windows = self._subtract_fixed_tasks(windows, db)
        windows = self._subtract_dead_zones(windows)
        
        valid_windows = {}
        for date_str, ws in windows.items():
            for w in ws:
                if self._parse_time(w.end_time) > self._parse_time(w.start_time):
                    if date_str not in valid_windows:
                        valid_windows[date_str] = []
                    valid_windows[date_str].append(w)
        
        return valid_windows
    
    
    def _subtract_fixed_tasks(
        self,
        windows: Dict[str, List[TimeWindow]],
        db: Session,
    ) -> Dict[str, List[TimeWindow]]:
        """Subtract slots occupied by fixed tasks."""
        fixed_tasks = db.query(ProvisionalSlot).filter(ProvisionalSlot.fixed == True).all()
        
        for slot in fixed_tasks:
            date_str = slot.start.strftime("%Y-%m-%d")
            if date_str in windows:
                new_windows = []
                for window in windows[date_str]:
                    if slot.start.time() >= self._parse_time(window.end_time) or slot.end.time() <= self._parse_time(window.start_time):
                        new_windows.append(window)
                    else:
                        if self._parse_time(window.start_time) < slot.start.time():
                            new_windows.append(TimeWindow(
                                date=date_str,
                                start_time=window.start_time,
                                end_time=slot.start.strftime("%H:%M"),
                            ))
                        if slot.end.time() < self._parse_time(window.end_time):
                            new_windows.append(TimeWindow(
                                date=date_str,
                                start_time=slot.end.strftime("%H:%M"),
                                end_time=window.end_time,
                            ))
                windows[date_str] = new_windows
        
        return windows
    
    
    def _subtract_dead_zones(
        self,
        windows: Dict[str, List[TimeWindow]],
    ) -> Dict[str, List[TimeWindow]]:
        """Subtract dead zones from time windows."""
        for zone_start, zone_end in DEAD_ZONES:
            for date_str in windows:
                new_windows = []
                for window in windows[date_str]:
                    ws = self._parse_time(window.start_time)
                    we = self._parse_time(window.end_time)
                    zs = self._parse_time(zone_start)
                    ze = self._parse_time(zone_end)
                    
                    if we <= zs or ws >= ze:
                        new_windows.append(window)
                    else:
                        if ws < zs:
                            new_windows.append(TimeWindow(
                                date=date_str,
                                start_time=window.start_time,
                                end_time=zone_start,
                            ))
                        if we > ze:
                            new_windows.append(TimeWindow(
                                date=date_str,
                                start_time=zone_end,
                                end_time=window.end_time,
                            ))
                windows[date_str] = new_windows
        
        return windows
    
    
    # ============================================================================
    # PRIVATE: SLOT GENERATOR
    # ============================================================================
    
    def _generate_slots(
        self,
        windows: Dict[str, List[TimeWindow]],
        duration_minutes: int,
    ) -> List[datetime]:
        """Split windows into 15-min slot start times."""
        slots: List[datetime] = []
        
        for date_str, ws in windows.items():
            for window in ws:
                start_minutes = self._parse_time(window.start_time)
                end_minutes = self._parse_time(window.end_time)
                
                window_end_total_minutes = end_minutes[0] * 60 + end_minutes[1]
                duration_total_minutes = self._round_up_to_interval(duration_minutes)
                valid_end_minutes = window_end_total_minutes - duration_total_minutes
                
                if valid_end_minutes <= 0:
                    continue
                
                current_hour = start_minutes[0]
                current_minute = start_minutes[1]
                
                while (current_hour * 60 + current_minute) <= valid_end_minutes:
                    slot_dt = datetime.strptime(f"{date_str} {current_hour:02d}:{current_minute:02d}", "%Y-%m-%d %H:%M")
                    slots.append(slot_dt)
                    
                    current_minute += SLOT_INTERVAL_MINUTES
                    if current_minute >= 60:
                        current_hour += 1
                        current_minute = 0
        
        slots.sort()
        return slots
    
    
    # ============================================================================
    # PRIVATE: SCORER
    # ============================================================================
    
    def _score_slot(
        self,
        slot_start: datetime,
        slot_end: datetime,
        task: Task,
        db: Session,
    ) -> float:
        """Calculate total score for a slot."""
        score = BASE_SLOT_SCORE
        
        score += self._get_location_boost(slot_start, task, db)
        score += self._get_free_slot_boost(slot_start, slot_end, db)
        score += self._get_time_score_boost(slot_start, task, db)
        score += self._get_urgency_boost(slot_start, task)
        score += self._get_continuity_boost(slot_start, db)
        score -= self._get_overlap_penalty(slot_start, slot_end, db)
        
        return score
    
    
    def _get_location_boost(
        self,
        slot_start: datetime,
        task: Task,
        db: Session,
    ) -> float:
        """Calculate location continuity boost."""
        if not task.location:
            return 0.0
        
        task_location = task.location.name
        
        before = db.query(ProvisionalSlot).filter(
            ProvisionalSlot.end <= slot_start,
            ProvisionalSlot.end > slot_start - timedelta(hours=2),
        ).order_by(ProvisionalSlot.end.desc()).first()
        
        after = db.query(ProvisionalSlot).filter(
            ProvisionalSlot.start >= slot_start,
            ProvisionalSlot.start < slot_start + timedelta(hours=2),
        ).order_by(ProvisionalSlot.start).first()
        
        continuity_count = 0
        
        if before and before.location == task_location:
            continuity_count += 0.5
        
        if after and after.location == task_location:
            continuity_count += 0.5
        
        return LOCATION_BASE_BOOST * continuity_count
    
    
    def _get_free_slot_boost(
        self,
        slot_start: datetime,
        slot_end: datetime,
        db: Session,
    ) -> float:
        """Calculate free slot boost."""
        overlapping = self._get_overlapping_tasks(slot_start, slot_end, db)
        
        if not overlapping:
            return FREE_SLOT_BOOST
        
        return 0.0
    
    
    def _get_time_score_boost(
        self,
        slot_start: datetime,
        task: Task,
        db: Session,
    ) -> float:
        """Calculate time preference score boost."""
        time_key = slot_start.strftime("%H:%M")
        
        if task.task_statistics_id:
            stats = db.query(TaskStatistics).filter(
                TaskStatistics.id == task.task_statistics_id
            ).first()
            if stats and stats.task_time_scores:
                if time_key in stats.task_time_scores:
                    score = stats.task_time_scores[time_key]
                    return TIME_SCORE_AMPLIFIER * (score / 10)
        
        if task.associated_task_statistics_id:
            stats = db.query(TaskStatistics).filter(
                TaskStatistics.id == task.associated_task_statistics_id
            ).first()
            if stats and stats.task_time_scores:
                if time_key in stats.task_time_scores:
                    score = stats.task_time_scores[time_key]
                    return TIME_SCORE_AMPLIFIER * (score / 10)
        
        task_cats = (
            db.query(TaskCategory)
            .filter(TaskCategory.task_id == task.id)
            .order_by(TaskCategory.priority)
            .all()
        )
        
        for tc in task_cats:
            cat_stats = db.query(CategoryStatistics).filter(
                CategoryStatistics.category_id == tc.category_id
            ).first()
            if cat_stats and cat_stats.category_time_scores:
                if time_key in cat_stats.category_time_scores:
                    score = cat_stats.category_time_scores[time_key]
                    return TIME_SCORE_AMPLIFIER * (score / 10)
        
        return 0.0
    
    
    def _get_urgency_boost(
        self,
        slot_start: datetime,
        task: Task,
    ) -> float:
        """Calculate urgency boost (earlier slots get higher boost)."""
        total_minutes = HORIZON_DAYS * 24 * 60
        
        now = datetime.utcnow()
        
        if slot_start <= now:
            logger.warning(f"Slot {slot_start} is in the past (now: {now})")
            return -1.0
        
        slot_minutes = (slot_start - now).total_seconds() / 60
        
        position_ratio = slot_minutes / total_minutes
        
        urgency_value = (task.urgency or 0.5) * 0.5 + (task.importance or 0.5) * 0.5
        
        return URGENCY_AMPLIFIER * urgency_value * (1 - position_ratio)
    
    
    def _get_continuity_boost(
        self,
        slot_start: datetime,
        db: Session,
    ) -> float:
        """Calculate proximity boost to previous task."""
        prev_task = db.query(ProvisionalSlot).filter(
            ProvisionalSlot.end <= slot_start,
        ).order_by(ProvisionalSlot.end.desc()).first()
        
        if not prev_task:
            return 0.0
        
        minutes_diff = (slot_start - prev_task.end).total_seconds() / 60
        
        slots_diff = round(minutes_diff / SLOT_INTERVAL_MINUTES)
        
        if slots_diff <= 0:
            return 0.0
        elif slots_diff == 1:
            return CONTINUITY_BASE_BOOST * 0.5
        elif slots_diff == 2:
            return CONTINUITY_BASE_BOOST * 1.0
        elif slots_diff == 3:
            return CONTINUITY_BASE_BOOST * 0.5
        else:
            return 0.0
    
    
    def _get_overlap_penalty(
        self,
        slot_start: datetime,
        slot_end: datetime,
        db: Session,
    ) -> float:
        """Calculate overlap penalty."""
        overlapping = self._get_overlapping_tasks(slot_start, slot_end, db)
        
        if not overlapping:
            return 0.0
        
        return OVERLAP_BASE_PENALTY * len(overlapping)
    
    
    # ============================================================================
    # PRIVATE: DISPLACEMENT HANDLER
    # ============================================================================
    
    def _handle_displacement(
        self,
        task: Task,
        slot_start: datetime,
        slot_end: datetime,
        db: Session,
        layer: int = 1,
    ) -> SchedulingResult:
        """Try to place task in slot, displacing if needed."""
        overlapping = self._get_overlapping_tasks(slot_start, slot_end, db)
        
        if not overlapping:
            return self._place_task(task, slot_start, slot_end, db, [])
        
        fixed_tasks = [t for t in overlapping if t.fixed]
        if fixed_tasks:
            return SchedulingResult(
                success=False,
                task_id=task.id,
                slot_start=slot_start,
                slot_end=slot_end,
                displaced_tasks=[],
                message="Slot occupied by fixed task",
            )
        
        sorted_tasks = sorted(overlapping, key=lambda t: t.value or 0.0)
        displaced_ids: List[UUID] = []
        
        for existing in sorted_tasks:
            if not self._can_displace(task, existing):
                return SchedulingResult(
                    success=False,
                    task_id=task.id,
                    slot_start=slot_start,
                    slot_end=slot_end,
                    displaced_tasks=displaced_ids,
                    message=f"Cannot displace {existing.task_id}: value threshold not met",
                )
            
            displaced_task = db.query(Task).filter(Task.id == existing.task_id).first()
            if not displaced_task:
                logger.warning(f"Task {existing.task_id} not found for displacement")
                continue
            
            old_start = existing.start
            old_end = existing.end
            
            db.delete(existing)
            
            reschedule_result = self._try_reschedule_task(displaced_task, db, layer=layer + 1)
            
            if not reschedule_result.success:
                db.rollback()
                return SchedulingResult(
                    success=False,
                    task_id=task.id,
                    slot_start=slot_start,
                    slot_end=slot_end,
                    displaced_tasks=displaced_ids,
                    message=f"Cannot displace {existing.task_id}: cannot be rescheduled",
                )
            
            new_change = ScheduleChange(
                provisional_schedule_slot_id=reschedule_result.slot_id,
                change_type="move",
                old_slot_start=old_start,
                old_slot_end=old_end,
                new_slot_start=reschedule_result.slot_start,
                new_slot_end=reschedule_result.slot_end,
            )
            db.add(new_change)
            displaced_ids.append(existing.task_id)
        
        return self._place_task(task, slot_start, slot_end, db, displaced_ids)
    
    
    def _can_displace(self, new_task: Task, existing: ProvisionalSlot) -> bool:
        """Check if new_task can displace existing task."""
        existing_value = existing.value or 0.0
        new_value = new_task.value or 0.0
        
        return new_value > existing_value * VALUE_THRESHOLD
    
    
    def _place_task(
        self,
        task: Task,
        slot_start: datetime,
        slot_end: datetime,
        db: Session,
        displaced_ids: List[UUID],
    ) -> SchedulingResult:
        """Place task in provisional schedule."""
        existing = db.query(ProvisionalSlot).filter(
            ProvisionalSlot.task_id == task.id
        ).first()
        
        change_type = "move" if existing else "insert"
        
        if existing:
            db.delete(existing)
        
        slot = ProvisionalSlot(
            task_id=task.id,
            start=slot_start,
            end=slot_end,
            value=task.value,
            fixed=task.fixed_time,
            location=task.location.name if task.location else None,
        )
        db.add(slot)
        db.flush()

        change = ScheduleChange(
            provisional_schedule_slot_id=slot.id,
            change_type=change_type,
            old_slot_start=existing.start if existing else None,
            old_slot_end=existing.end if existing else None,
            new_slot_start=slot_start,
            new_slot_end=slot_end,
        )
        db.add(change)
        db.commit()

        return SchedulingResult(
            success=True,
            task_id=task.id,
            slot_id=slot.id,
            slot_start=slot_start,
            slot_end=slot_end,
            displaced_tasks=displaced_ids,
            message="Task scheduled successfully",
        )
    
    
    # ============================================================================
    # PRIVATE: UTILITIES
    # ============================================================================
    
    def _get_overlapping_tasks(
        self,
        slot_start: datetime,
        slot_end: datetime,
        db: Session,
    ) -> List[ProvisionalSlot]:
        """Get all slots that overlap with the given time range."""
        return db.query(ProvisionalSlot).filter(
            ProvisionalSlot.start < slot_end,
            ProvisionalSlot.end > slot_start,
        ).all()
    
    
    def _round_up_to_interval(self, minutes: int) -> int:
        """Round minutes up to nearest slot interval."""
        return ((minutes + SLOT_INTERVAL_MINUTES - 1) // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES
    
    
    def _round_down_to_interval(self, dt: datetime, interval: int) -> datetime:
        """Round datetime down to nearest interval."""
        total_minutes = dt.hour * 60 + dt.minute
        rounded = (total_minutes // interval) * interval
        return dt.replace(hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0)
    
    
    def _calculate_end(self, start: datetime, duration_minutes: int) -> datetime:
        """Calculate end time from start and duration."""
        rounded_duration = self._round_up_to_interval(duration_minutes)
        return start + timedelta(minutes=rounded_duration)
    
    
    def _calculate_fixed_task_end(self, fixed_start: datetime, duration_minutes: int) -> datetime:
        """Calculate end time for fixed task."""
        raw_end = fixed_start + timedelta(minutes=duration_minutes)
        return self._round_up_to_interval_dt(raw_end)
    
    
    def _round_up_to_interval_dt(self, dt: datetime) -> datetime:
        """Round datetime UP to nearest interval."""
        total_minutes = dt.hour * 60 + dt.minute
        rounded = ((total_minutes + SLOT_INTERVAL_MINUTES - 1) // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES
        if rounded >= 24 * 60:
            return dt.replace(hour=23, minute=59, second=59, microsecond=0)
        return dt.replace(hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0)
    
    
    def _parse_time(self, time_str: str) -> Tuple[int, int]:
        """Parse HH:MM string to (hour, minute) tuple."""
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])


# ============================================================================
# EXPORT SINGLETON INSTANCE
# ============================================================================

schedule_engine = ScheduleEngine()