# Stats Recorder — Technical Documentation
**Version:** 1.0 (Final)
**Last Updated:** April 18, 2026
**Competition:** ONIA 2026

---

## 1. Overview

The Stats Recorder is the fifth stage in the VM.AI pipeline. It synchronously updates behavioral statistics when tasks are committed or rated.

### Key Design Principles
- **Synchronous Execution**: Runs in same DB transaction as triggering action to eliminate race conditions
- **Two Denominators**: Separates plan averages (records) from delta averages (completed_count)
- **Radial Decay**: Time preferences decay over time blocks to adapt to schedule changes

### What It Does
- Updates task statistics when tasks are committed (planned)
- Updates task statistics when tasks are rated (completed)
- Updates category statistics for all task categories
- Handles location tracking
- Applies radial decay to time preferences

### What It Does NOT Do
- Handle scheduling decisions
- Make enrichment or matching decisions
- Run asynchronously (for MVP)

---

## 2. Position in Pipeline

```
Task Created → Task Matching → Enrichment → Scheduler
                                    ↓
                             Stats Recorder (on commit)
                                    ↓
                             Statistics Updated
```

Also triggered separately when user rates a task:
```
User Rates Task → Stats Recorder (on rate)
                        ↓
              Statistics Updated
```

---

## 3. Two Denominators

The system uses two separate denominators to maintain mathematical soundness:

| Average Type | Denominator | When Updated |
|--------------|--------------|--------------|
| **Plan averages** | `records` | On task commit |
| **Delta averages** | `completed_count` | On task rating |

### Plan Averages (on commit)
```python
new_avg = (old_avg * records + new_value) / (records + 1)
records += 1
```

### Delta Averages (on rating)
```python
new_delta_avg = (old_delta_avg * completed_count + delta) / (completed_count + 1)
completed_count += 1
```

---

## 4. Update Triggers

### 4.1 On Task Commit
When a task is created or modified:

| Field | Update |
|-------|--------|
| `avg_duration[bucket]` | Recalculate with weighted average |
| `avg_difficulty` | Recalculate with weighted average |
| `avg_duration_delta` | NOT updated (no actual yet) |
| `avg_difficulty_delta` | NOT updated (no actual yet) |
| `records` | Increment by 1 |

### 4.2 On Task Rating
When user rates a completed task:

| Field | Update |
|-------|--------|
| `avg_duration_delta[bucket]` | Recalculate with weighted average |
| `avg_difficulty_delta` | Recalculate with weighted average |
| `completed_count` | Increment by 1 |

When user rates an incomplete task:

| Field | Update |
|-------|--------|
| `uncompleted_count` | Increment by 1 |

---

## 5. Duration Bucket Logic

Duration is bucketed by difficulty (0.0, 0.5, 1.0):

```
bucket = round(difficulty * 2) / 2
```

Example:
- Difficulty 0.7 → bucket 0.5
- Difficulty 0.3 → bucket 0.0

The Stats Recorder updates the correct bucket based on the actual or committed difficulty.

---

## 6. Location Tracking

### Task Statistics Locations
```python
# Increment count for location
tasks_statistics_locations[location_id].count += 1
```

### Category Statistics Locations
```python
# Increment count for each category's location
category_statistics_locations[category_id][location_id].count += 1
```

---

## 7. Radial Decay

Time preferences decay over time blocks to adapt to schedule changes:

```python
def apply_radial_decay(time_scores: dict, blocks: int) -> dict:
    decay_factor = 0.25
    for time_slot, score in time_scores.items():
        time_scores[time_slot] = score * (1 - blocks * decay_factor)
    return time_scores
```

Applied when:
- Task is scheduled in a time slot it previously had high preference for
- Task is dislocated from preferred time slot

---

## 8. API Endpoint

### POST /tasks/{id}/rate

**Request:**
```json
{
    "completed": true,
    "actual_duration": 75,
    "actual_difficulty": 0.8
}
```

**Validation:**
- If `completed=true`: `actual_duration` and `actual_difficulty` required
- If `completed=false`: Cannot send actual values

**Response:**
```json
{
    "success": true,
    "task_id": "uuid",
    "stats_updated": true
}
```

---

## 9. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Update behavioral statistics |
| **Execution** | Synchronous (same transaction) |
| **Denominators** | records (plan), completed_count (delta) |
| **Triggers** | Task commit, Task rating |
| **Location Tracking** | Via junction tables |
| **Radial Decay** | Applied on dislocation |

---

*Document prepared for ONIA 2026.*