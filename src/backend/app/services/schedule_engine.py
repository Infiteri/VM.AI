"""
Schedule Engine Service
Part of VM.AI pipeline - Stage 4

Handles:
- Constraint solving
- Slot generation
- Scoring
- Displacement handling

Version: 1.0
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.schedule import ProvisionalSlot, MainScheduleSlot
from app.models.workflow import UnscheduledTask, ScheduleChange
from app.models.statistics import TaskStatistics, CategoryStatistics
from app.models.task_category import TaskCategory
from app.models.category import Category
from app.core.logging_config import setup_logging

logger = setup_logging()


# ============================================================================
# CONSTANTS
# ============================================================================

SLOT_INTERVAL_MINUTES = 15
HORIZON_DAYS = 7
TOP_N_CANDIDATES = 15
VALUE_THRESHOLD = 1.25
MAX_DISPLACEMENT_LAYERS = 1
TIMEOUT_SECONDS = 12

LOCATION_BASE_BOOST = 0.25
FREE_SLOT_BOOST = 0.1
TIME_SCORE_AMPLIFIER = 0.3
URGENCY_AMPLIFIER = 0.3
CONTINUITY_BASE_BOOST = 0.1
OVERLAP_BASE_PENALTY = 0.15
BASE_SLOT_SCORE = 1.0

DEAD_ZONES = [
    ("23:00", "06:00"),
    ("13:00", "15:00"),
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


@dataclass
class SchedulingResult:
    """Result of scheduling a single task."""
    success: bool
    task_id: Optional[UUID]
    slot_start: Optional[datetime]
    slot_end: Optional[datetime]
    displaced_tasks: List[UUID]
    message: str


@dataclass
class BatchSchedulingResult:
    """Result of batch scheduling."""
    scheduled_count: int
    failed_count: int
    results: List[SchedulingResult]
    execution_time_ms: int


# ============================================================================
# PUBLIC API
# ============================================================================

def schedule_single_task(task: Task, db: Session) -> SchedulingResult:
    """
    Schedule a single task into the provisional schedule.
    
    Returns:
        SchedulingResult with success status and slot info.
    """
    logger.info(f"Scheduling task: {task.name} (ID: {task.id})")
    
    if task.fixed_time:
        return _schedule_fixed_task(task, db)
    else:
        return _schedule_flexible_task(task, db)


def schedule_batch(db: Session, timeout: int = TIMEOUT_SECONDS) -> BatchSchedulingResult:
    """
    Schedule all tasks from unscheduled_tasks queue.
    FIFO order, per-task writes.
    
    Returns:
        BatchSchedulingResult with count and details.
    """
    start_time = datetime.utcnow()
    logger.info("Starting batch scheduling")
    
    unscheduled = (
        db.query(UnscheduledTask)
        .join(Task)
        .order_by(UnscheduledTask.created_at)
        .all()
    )
    
    results: List[SchedulingResult] = []
    scheduled_count = 0
    failed_count = 0
    
    for entry in unscheduled:
        task = entry.task
        if not task:
            logger.warning(f"Task not found for entry: {entry.task_id}")
            failed_count += 1
            continue
        
        result = schedule_single_task(task, db)
        results.append(result)
        
        if result.success:
            scheduled_count += 1
            db.delete(entry)
            db.commit()
        else:
            failed_count += 1
        
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
        results=results,
        execution_time_ms=execution_time_ms,
    )


# ============================================================================
# FIXED TASK SCHEDULING
# ============================================================================

def _schedule_fixed_task(task: Task, db: Session) -> SchedulingResult:
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
    
    fixed_start = _round_down_to_interval(task.fixed_start, SLOT_INTERVAL_MINUTES)
    fixed_end = _calculate_fixed_task_end(task.fixed_start, task.duration)
    
    logger.debug(f"Fixed task at {fixed_start} - {fixed_end}")
    
    overlapping = _get_overlapping_tasks(fixed_start, fixed_end, db)
    
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
            reschedule_result = _try_reschedule_task(existing_task_for_displacement, db, layer=1)
            
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
                task_id=displaced_id,
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
    
    change = ScheduleChange(
        task_id=task.id,
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
        slot_start=fixed_start,
        slot_end=fixed_end,
        displaced_tasks=displaced_ids,
        message="Task scheduled at fixed time",
    )


# ============================================================================
# FLEXIBLE TASK SCHEDULING
# ============================================================================

def _schedule_flexible_task(task: Task, db: Session) -> SchedulingResult:
    """Schedule a flexible task with full scheduling pipeline."""
    logger.debug(f"Flexible task: {task.name}")
    
    windows = _get_time_windows(task, db)
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
    slots = _generate_slots(windows, duration)
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
        duration = task.duration or 30
        slot_end = _calculate_end(slot_start, duration)
        score = _score_slot(slot_start, slot_end, task, db)
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
        result = _handle_displacement(task, candidate.start, candidate.end, db)
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
# CONSTRAINT SOLVER
# ============================================================================

def _get_time_windows(task: Task, db: Session) -> Dict[str, List[TimeWindow]]:
    """
    Build viable time windows for task.
    
    Returns:
        Dict keyed by date: {"2026-04-20": [TimeWindow, ...], ...}
    """
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
    
    windows = _subtract_fixed_tasks(windows, db)
    windows = _subtract_dead_zones(windows)
    
    valid_windows = {}
    for date_str, ws in windows.items():
        for w in ws:
            if _parse_time(w.end_time) > _parse_time(w.start_time):
                if date_str not in valid_windows:
                    valid_windows[date_str] = []
                valid_windows[date_str].append(w)
    
    return valid_windows


def _subtract_fixed_tasks(
    windows: Dict[str, List[TimeWindow]], db: Session
) -> Dict[str, List[TimeWindow]]:
    """Subtract slots occupied by fixed tasks."""
    fixed_tasks = db.query(ProvisionalSlot).filter(ProvisionalSlot.fixed == True).all()
    
    for slot in fixed_tasks:
        date_str = slot.start.strftime("%Y-%m-%d")
        if date_str in windows:
            new_windows = []
            for window in windows[date_str]:
                if slot.start.time() >= _parse_time(window.end_time) or slot.end.time() <= _parse_time(window.start_time):
                    new_windows.append(window)
                else:
                    if _parse_time(window.start_time) < slot.start.time():
                        new_windows.append(TimeWindow(
                            date=date_str,
                            start_time=window.start_time,
                            end_time=slot.start.strftime("%H:%M"),
                        ))
                    if slot.end.time() < _parse_time(window.end_time):
                        new_windows.append(TimeWindow(
                            date=date_str,
                            start_time=slot.end.strftime("%H:%M"),
                            end_time=window.end_time,
                        ))
            windows[date_str] = new_windows
    
    return windows


def _subtract_dead_zones(
    windows: Dict[str, List[TimeWindow]]
) -> Dict[str, List[TimeWindow]]:
    """Subtract dead zones from time windows."""
    for zone_start, zone_end in DEAD_ZONES:
        for date_str in windows:
            new_windows = []
            for window in windows[date_str]:
                ws = _parse_time(window.start_time)
                we = _parse_time(window.end_time)
                zs = _parse_time(zone_start)
                ze = _parse_time(zone_end)
                
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
# SLOT GENERATOR
# ============================================================================

def _generate_slots(
    windows: Dict[str, List[TimeWindow]],
    duration_minutes: int,
) -> List[datetime]:
    """
    Split windows into 15-min slot start times.
    
    IMPORTANT: Accounts for task duration.
    Last valid slot start = window_end - duration (task must complete within window)
    """
    slots: List[datetime] = []
    
    for date_str, ws in windows.items():
        for window in ws:
            start_minutes = _parse_time(window.start_time)
            end_minutes = _parse_time(window.end_time)
            
            window_end_total_minutes = end_minutes[0] * 60 + end_minutes[1]
            duration_total_minutes = _round_up_to_interval(duration_minutes)
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
# SCORER
# ============================================================================

def _score_slot(
    slot_start: datetime,
    slot_end: datetime,
    task: Task,
    db: Session,
) -> float:
    """Calculate total score for a slot."""
    score = BASE_SLOT_SCORE
    
    score += _get_location_boost(slot_start, slot_end, task, db)
    score += _get_free_slot_boost(slot_start, slot_end, db)
    score += _get_time_score_boost(slot_start, task, db)
    score += _get_urgency_boost(slot_start, task)
    score += _get_continuity_boost(slot_start, db)
    score -= _get_overlap_penalty(slot_start, slot_end, db)
    
    return score


def _get_location_boost(
    slot_start: datetime,
    slot_end: datetime,
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
        ProvisionalSlot.start >= slot_end,
        ProvisionalSlot.start < slot_end + timedelta(hours=2),
    ).order_by(ProvisionalSlot.start).first()
    
    continuity_count = 0
    
    if before and before.location == task_location:
        continuity_count += 0.5
    
    if after and after.location == task_location:
        continuity_count += 0.5
    
    return LOCATION_BASE_BOOST * continuity_count


def _get_free_slot_boost(
    slot_start: datetime,
    slot_end: datetime,
    db: Session,
) -> float:
    """Calculate free slot boost (no overlap = boost)."""
    overlapping = _get_overlapping_tasks(slot_start, slot_end, db)
    
    if not overlapping:
        return FREE_SLOT_BOOST
    
    return 0.0


def _get_time_score_boost(
    slot_start: datetime,
    task: Task,
    db: Session,
) -> float:
    """Calculate time preference score boost."""
    time_key = slot_start.strftime("%H:%M")
    score = 0.0
    
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
    slot_start: datetime,
    task: Task,
) -> float:
    """Calculate urgency boost (earlier slots get higher boost).
    
    Formula: boost = URGENCY_AMPLIFIER * urgency_value * (1 - position_ratio)
    Earlier slots (low position_ratio) → higher boost
    Later slots (high position_ratio) → lower boost
    
    Args:
        slot_start: When the slot begins
        task: Task with urgency and importance values
    """
    total_minutes = HORIZON_DAYS * 24 * 60
    
    # Calculate minutes from now to slot_start (includes days automatically)
    now = datetime.utcnow()
    
    # Slot cannot be in the past - return negative score
    if slot_start <= now:
        logger.warning(f"Slot {slot_start} is in the past (now: {now})")
        return -1.0
    
    slot_minutes = (slot_start - now).total_seconds() / 60
    
    # Position ratio: 0.0 = start of horizon, 1.0 = end of horizon
    position_ratio = slot_minutes / total_minutes
    
    urgency_value = (task.urgency or 0.5) * 0.5 + (task.importance or 0.5) * 0.5
    
    # Linear formula: higher boost for earlier slots
    return URGENCY_AMPLIFIER * urgency_value * (1 - position_ratio)


def _get_continuity_boost(
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
    slot_start: datetime,
    slot_end: datetime,
    db: Session,
) -> float:
    """Calculate overlap penalty."""
    overlapping = _get_overlapping_tasks(slot_start, slot_end, db)
    
    if not overlapping:
        return 0.0
    
    return OVERLAP_BASE_PENALTY * len(overlapping)


# ============================================================================
# DISPLACEMENT HANDLER
# ============================================================================

def _try_reschedule_task(task: Task, db: Session, layer: int = 1) -> SchedulingResult:
    """
    Try to reschedule a displaced task.
    
    Uses full scheduling pipeline but with layer limit.
    """
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
        return _schedule_fixed_task(task, db)
    else:
        return _schedule_flexible_task(task, db)


def _handle_displacement(
    task: Task,
    slot_start: datetime,
    slot_end: datetime,
    db: Session,
    layer: int = 1,
) -> SchedulingResult:
    """Try to place task in slot, displacing if needed."""
    overlapping = _get_overlapping_tasks(slot_start, slot_end, db)
    
    if not overlapping:
        return _place_task(task, slot_start, slot_end, db, [])
    
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
        if not _can_displace(task, existing):
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
        
        reschedule_result = _try_reschedule_task(displaced_task, db, layer=layer + 1)
        
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
            task_id=existing.task_id,
            change_type="move",
            old_slot_start=old_start,
            old_slot_end=old_end,
            new_slot_start=reschedule_result.slot_start,
            new_slot_end=reschedule_result.slot_end,
        )
        db.add(new_change)
        displaced_ids.append(existing.task_id)
    
    return _place_task(task, slot_start, slot_end, db, displaced_ids)


def _can_displace(new_task: Task, existing: ProvisionalSlot) -> bool:
    """Check if new_task can displace existing task."""
    existing_value = existing.value or 0.0
    new_value = new_task.value or 0.0
    
    return new_value > existing_value * VALUE_THRESHOLD


def _place_task(
    task: Task,
    slot_start: datetime,
    slot_end: datetime,
    db: Session,
    displaced_ids: List[UUID],
) -> SchedulingResult:
    """Place task in provisional schedule."""
    # Check if task already exists in provisional_schedule
    existing = db.query(ProvisionalSlot).filter(
        ProvisionalSlot.task_id == task.id
    ).first()
    
    change_type = "move" if existing else "insert"
    
    # Remove old slot if exists (task was rescheduled)
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
    
    change = ScheduleChange(
        task_id=task.id,
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
        slot_start=slot_start,
        slot_end=slot_end,
        displaced_tasks=displaced_ids,
        message="Task scheduled successfully",
    )


# ============================================================================
# UTILITIES
# ============================================================================

def _calculate_fixed_task_end(fixed_start: datetime, duration_minutes: int) -> datetime:
    """
    Calculate end time for fixed task.
    
    Unlike regular tasks, fixed tasks calculate end from ORIGINAL start time,
    then normalize both start and end to slot boundaries.
    
    Example:
        fixed_start = 13:40, duration = 30 min
        Raw end = 13:40 + 30 = 14:10
        Normalize end: 14:10 → 14:15 (round up to interval)
        Result: 14:15
    """
    raw_end = fixed_start + timedelta(minutes=duration_minutes)
    return _round_up_to_interval_dt(raw_end)


def _round_up_to_interval_dt(dt: datetime) -> datetime:
    """Round datetime UP to nearest interval."""
    total_minutes = dt.hour * 60 + dt.minute
    rounded = ((total_minutes + SLOT_INTERVAL_MINUTES - 1) // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES
    if rounded >= 24 * 60:
        return dt.replace(hour=23, minute=59, second=59, microsecond=0)
    return dt.replace(hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0)

def _get_overlapping_tasks(
    slot_start: datetime,
    slot_end: datetime,
    db: Session,
) -> List[ProvisionalSlot]:
    """Get all slots that overlap with the given time range."""
    overlapping = db.query(ProvisionalSlot).filter(
        ProvisionalSlot.start < slot_end,
        ProvisionalSlot.end > slot_start,
    ).all()
    return overlapping


def _round_up_to_interval(minutes: int) -> int:
    """Round minutes up to nearest slot interval."""
    return ((minutes + SLOT_INTERVAL_MINUTES - 1) // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES


def _round_down_to_interval(dt: datetime, interval: int) -> datetime:
    """Round datetime down to nearest interval."""
    total_minutes = dt.hour * 60 + dt.minute
    rounded = (total_minutes // interval) * interval
    return dt.replace(hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0)


def _calculate_end(start: datetime, duration_minutes: int) -> datetime:
    """Calculate end time from start and duration."""
    rounded_duration = _round_up_to_interval(duration_minutes)
    return start + timedelta(minutes=rounded_duration)


def _parse_time(time_str: str) -> Tuple[int, int]:
    """Parse HH:MM string to (hour, minute) tuple."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def _check_overlap(
    start1: datetime,
    end1: datetime,
    start2: datetime,
    end2: datetime,
) -> bool:
    """Check if two time ranges overlap."""
    return start1 < end2 and end1 > start2


# ============================================================================
# SERVICE INSTANCE
# ============================================================================

schedule_engine = {
    "schedule_single": schedule_single_task,
    "schedule_batch": schedule_batch,
}