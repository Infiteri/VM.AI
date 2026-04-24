# Scheduling Engine — Technical Documentation
**Version:** 1.0 (Final)
**Last Updated:** April 18, 2026
**Competition:** ONIA 2026

---

## 1. Overview

The Scheduling Engine is the fourth stage in the VM.AI pipeline. It takes unscheduled tasks and places them into the provisional schedule using a stable incremental algorithm.

### Key Design Principles
- **Stable Incremental**: Only schedules new tasks, doesn't reschedule everything
- **1-Layer Displacement**: Tasks can only be pushed 1 slot max
- **12s Timeout**: Hard timeout to prevent hanging
- **25% Value Threshold**: Won't displace tasks worth >25% more

### What It Does
- Fetches unscheduled tasks (FIFO order)
- Applies constraint solving
- Scores tasks against available slots
- Writes to provisional_schedule
- Records schedule_changes

### What It Does NOT Do
- Handle NLP parsing
- Make enrichment decisions
- Update statistics

---

## 2. Position in Pipeline

```
Unscheduled Tasks Queue
    ↓
Scheduler
    ↓
Constraint Solving → Top-15 Pruning → Stable Scoring
    ↓
Provisional Schedule → Commit
    ↓
Main Schedule
```

---

## 3. Algorithm

### 3.1 Fetch Phase
```python
tasks = db.query(Task).join(unscheduled_tasks).order_by(unscheduled_tasks.created_at).all()
```

### 3.2 Constraint Solving
For each task:
1. Find available time slots between start and deadline
2. Filter by duration
3. Check location conflicts

### 3.3 Top-15 Pruning
Only consider top 15 highest-value slots to prevent O(N²) explosion.

### 3.4 Scoring
```python
score = base_value
       + free_boost          # Tasks with flexible time get small boost
       - stability_penalty  # Displacing existing tasks costs points
       + location_boost     # Same location as nearby tasks
       - overlap_penalty    # Partial overlaps cost points
       + time_pref_boost     # User's preferred time slots
```

### 3.5 1-Layer Displacement
A task can only displace 1 other task max.

---

## 4. Constraints

| Constraint | Value | Description |
|-----------|-------|-------------|
| Timeout | 12s | Hard timeout to prevent hanging |
| Max Displacement | 1 | Only push 1 other task |
| Value Threshold | 25% | Won't displace if value diff >25% |
| Max Slots | 15 | Top 15 only to prune O(N²) |

---

## 5. Scoring Formula

### Variables
```python
base_value = task.value                    # From Enrichment
free_boost = 0.05 if task.fixed_time else 0
stability_penalty = 0.2 * displaced_count
location_boost = 0.1 if same_location else 0
overlap_penalty = 0.15 * overlap_fraction
time_pref_boost = time_scores.get(time_slot, 0)
```

### Final Score
```python
final_score = base_value + free_boost - stability_penalty + location_boost - overlap_penalty + time_pref_boost
```

---

## 6. Safety Guards

### Timeout
```python
if elapsed_time > 12:  # seconds
    break  # Commit partial progress
```

### Value Threshold
```python
existing_task_value = slot.task.value
new_task_value = task.value

if new_task_value > existing_task_value * 1.25:
    continue  # Don't displace
```

### Max Displacement
```python
if displaced_count > 1:
    break  # Stop adding to this slot
```

---

## 7. Output

### provisional_schedule
Writes to the provisional_schedule table:
- task_id
- start, end
- value (at scheduling time)
- fixed (from task)
- location

### schedule_changes
Records changes made:
- task_id
- change_type ("insert" or "move")
- new_slot_start
- new_slot_end

---

## 8. API Endpoints

### POST /schedule/batch
Runs the scheduler on all unscheduled tasks.

**Response:**
```json
{
    "success": true,
    "scheduled_count": 5,
    "unscheduled_remaining": [],
    "provisional_changes": [],
    "execution_time_ms": 3500
}
```

### GET /schedule?date=YYYY-MM-DD
Returns main schedule for a specific date.

**Response:**
```json
{
    "date": "2026-04-20",
    "tasks": [
        {
            "task_id": "uuid",
            "name": "Task name",
            "start": "2026-04-20T09:00:00",
            "end": "2026-04-20T10:00:00",
            "location": "Library",
            "rated": false
        }
    ]
}
```

---

## 9. Summary

| Aspect | Description |
|--------|-------------|
| **Algorithm** | Stable incremental placement |
| **Complexity** | O(N × 15) |
| **Timeout** | 12s hard |
| **Displacement** | 1-layer max |
| **Value Threshold** | 25% |
| **Output** | provisional_schedule + schedule_changes |

---

*Document prepared for ONIA 2026.*