```markdown
# Stats Recorder — Technical Documentation
VM.AI Project · ONIA 2026
Version 2.0 (Synchronous MVP + Plan/Reality Separation)

## 1. Overview

The Stats Recorder is the fifth and final stage in the VM.AI pipeline. It runs **synchronously during MVP** after user actions, updating all behavioral statistics that the Enrichment and Scheduler modules consume.

### What It Does
- Updates the task's own statistics (`task_statistics_id`) based on commits and completions
- Updates category-level statistics (`category_statistics`) in exact parallel
- Maintains a clean separation between **planned values** (updated on commit) and **reality deltas** (updated on completion)
- Calculates running averages incrementally without storing full history
- Manages time preference scores with radial decay and weekly normalization
- Increments commit counters and tracks location usage

### What It Does NOT Do
- Make scheduling decisions
- Parse natural language
- Update `associated_task_statistics_id` (read-only for Enrichment)
- Contain AI or machine learning models — strictly arithmetic operations
- Block user requests (executed in the same DB transaction as the triggering action for MVP)

## 2. Position in Pipeline

```text
User Action (Commit, Complete, Schedule, Commit Batch, Modify, Delete)
↓
Stats Recorder triggered synchronously (MVP)
↓
Reads current state from database
↓
Updates tasks_statistics (via task_statistics_id)
↓
Updates category_statistics (mirrors task-level behavior)
↓
Commits changes in same transaction as user action
↓
Other modules consume updated data on next request
```

## 3. Key Concepts

| Concept | Description |
|---------|-------------|
| `task_statistics_id` | Points to this task's own statistics row. Stats Recorder always updates this. |
| `associated_task_statistics_id` | Points to another task's row for enrichment. Stats Recorder **never** updates this. |
| `records` | Total number of task commits (creation + modifications). Denominator for **plan averages**. |
| `completed_count` | Number of successful completions with user ratings. Denominator for **delta averages**. |
| Plan Averages | `avg_duration`, `avg_difficulty` — track what the system *planned/committed*. |
| Delta Averages | `avg_duration_delta`, `avg_difficulty_delta` — track systematic bias between plan and reality. |
| Synchronous MVP | Updates run in the same request/transaction as the triggering action. Eliminates race conditions for competition scope. |

## 4. Data It Maintains

### 4.1 Task-Level Statistics (`tasks_statistics` table)
| Field | Type | Updated By |
|-------|------|------------|
| `id` | UUID | Task creation |
| `task_name` | TEXT | Task creation or name modification |
| `task_name_vector` | FLOAT[] | Task creation or name modification |
| `avg_duration` | INTEGER | Task commit (plan) |
| `avg_duration_delta` | INTEGER | Task completion (delta) |
| `avg_difficulty` | FLOAT | Task commit (plan) |
| `avg_difficulty_delta` | FLOAT | Task completion (delta) |
| `completed_count` | INTEGER | Task completion |
| `uncompleted_count` | INTEGER | Task uncompleted |
| `records` | INTEGER | Task commit |
| `location_counts` | JSONB | Task completion |
| `task_time_scores` | JSONB | Schedule / Commit / Modify events |

### 4.2 Category-Level Statistics (`category_statistics` table)
| Field | Type | Updated By |
|-------|------|------------|
| `category_id` | INTEGER | System seed |
| `category_name` | TEXT | System seed |
| `avg_duration` | JSONB | Task commit (plan, keyed by difficulty bucket) |
| `avg_duration_delta` | JSONB | Task completion (delta, keyed by difficulty bucket) |
| `avg_difficulty` | FLOAT | Task commit (plan) |
| `avg_difficulty_delta` | FLOAT | Task completion (delta) |
| `completed_count` | INTEGER | Task completion |
| `uncompleted_count` | INTEGER | Task uncompleted |
| `records` | INTEGER | Task commit |
| `location_counts` | JSONB | Task completion |
| `category_time_scores` | JSONB | Schedule / Commit / Modify events |

## 5. Running Average Formulas (Explicit)

The system uses two distinct denominator strategies to maintain mathematical soundness:

### 5.1 Plan Averages (Updated on Every Commit)
Tracks what the system committed. Denominator = `records`.
```text
new_avg_duration = (old_avg_duration × records + committed_duration) / (records + 1)
new_avg_difficulty = (old_avg_difficulty × records + committed_difficulty) / (records + 1)
```

### 5.2 Delta Averages (Updated Only on Completion/Rating)
Tracks systematic bias. Denominator = `completed_count`.
```text
new_avg_duration_delta = (old_avg_duration_delta × completed_count + duration_delta) / (completed_count + 1)
new_avg_difficulty_delta = (old_avg_difficulty_delta × completed_count + difficulty_delta) / (completed_count + 1)
```

### 5.3 Category-Level Bucket Handling
For `category_statistics`, duration averages are keyed by difficulty bucket: `bucket = round(difficulty × 2) / 2`
```text
new_avg_duration[bucket] = (old_avg_duration[bucket] × records + committed_duration) / (records + 1)
new_avg_duration_delta[bucket] = (old_avg_duration_delta[bucket] × completed_count + duration_delta) / (completed_count + 1)
```
> 💡 Category difficulty/difficulty_delta remain single floats per category, not bucketed.

## 6. Delta Calculation

Delta captures the systematic bias between a committed task value and the user's actual rating.

| Metric | Formula |
|--------|---------|
| Duration Delta | `actual_duration - committed_duration` |
| Difficulty Delta | `actual_difficulty - committed_difficulty` |

**Example:**  
Committed duration: `90 min` → User rated: `75 min` → `duration_delta = -15`  
Committed difficulty: `0.85` → User rated: `0.60` → `difficulty_delta = -0.25`

These deltas are consumed by Enrichment to calibrate future predictions: `predicted_duration = avg_duration + avg_duration_delta`.

## 7. Events That Trigger Stats Recording

All events execute synchronously in the same database transaction as the user action for MVP reliability.

### Event 1 — Task Commit (Creation or Modification)
**Trigger:** User creates or modifies task fields.  
**Updates:**
- `tasks_statistics.records += 1`
- `tasks_statistics.avg_duration = (avg_duration × records + committed_duration) / (records + 1)`
- `tasks_statistics.avg_difficulty = (avg_difficulty × records + committed_difficulty) / (records + 1)`
- Category-level: Same formulas applied to primary category (duration bucketed)
- If name changed: Update `task_name` and `task_name_vector`

### Event 2 — Task Completion (with Rating)
**Trigger:** User marks task completed and provides ratings.  
**Updates:**
- `tasks_statistics.completed_count += 1`
- `tasks_statistics.avg_duration_delta = (avg_duration_delta × completed_count + duration_delta) / (completed_count + 1)`
- `tasks_statistics.avg_difficulty_delta = (avg_difficulty_delta × completed_count + difficulty_delta) / (completed_count + 1)`
- `tasks_statistics.location_counts[location_used] += 1`
- Category-level: Mirrors exact task-level updates (delta bucketed by difficulty)

### Event 3 — Task Uncompleted
**Trigger:** User marks task as failed/cancelled.  
**Updates:**
- `tasks_statistics.uncompleted_count += 1`
- Category-level: `uncompleted_count += 1`

### Event 4 — Task Scheduled (Accepted without modification)
**Trigger:** User accepts scheduler's proposed slot.  
**Updates:**
- Radial boost `+1.0` applied to `task_time_scores` and `category_time_scores` (see Section 8)

### Event 5 — Schedule Committed (Batch Commit)
**Trigger:** User clicks "Commit" on Pending Changes Page.  
**Updates:**
- For every task in the committed schedule: Radial boost `+2.0` applied to time scores (see Section 8)

### Event 6 — Task Modified (Moved to Different Time)
**Trigger:** User moves a task from Schedule Changes List or Main Schedule.  
**Updates:**
- Original slot: Radial nerf `-2.0` (capped at `-10.0`)
- New slot: Radial boost `+1.0`
- Applied to both task-level and category-level time scores

### Event 7 — Task Deleted
**Trigger:** User deletes a task.  
**Updates:**
- No stats changes. Statistics row persists for historical matching.

### Event 8 — Task Modified (Fields Changed, Not Time)
**Trigger:** User modifies non-temporal fields.  
**Updates:**
- Treated exactly as Event 1 (increments `records`, updates plan averages)
- Time scores remain unchanged.

## 8. Time Preference Score Management

### 8.1 Radial Boost Formula
```text
blocks = abs(target_minutes - event_minutes) / 15
boost = base_boost × (1 - blocks × 0.25)
boost = max(0.0, boost)  # or min(-10.0, boost) for nerfs
```

### 8.2 Base Values
| Event | Base Boost | Applied To |
|-------|------------|------------|
| Task scheduled | `+1.0` | Task + Category |
| Schedule committed | `+2.0` | Task + Category (all committed tasks) |
| Move to new time | `+1.0` | Task + Category |
| Move from original | `-2.0` | Task + Category |

### 8.3 Atomic JSONB Updates
Computed in Python first, then applied in a single PostgreSQL query to prevent partial updates:
```sql
-- Python builds update_dict = {"10:00": 2.5, "10:15": 1.75}
UPDATE tasks_statistics 
SET task_time_scores = task_time_scores || %s
WHERE id = %s;
```
All scores are clamped to `[0.0, 10.0]` after application.

### 8.4 Weekly Normalization (Enabled by Default)
Prevents score saturation. Runs as a background cron job every Sunday at 00:00:
```sql
UPDATE tasks_statistics 
SET task_time_scores = jsonb_object_agg(
    key, 
    GREATEST(0.0, LEAST(10.0, value * 0.99))
) FROM jsonb_each(task_time_scores);
-- Same logic applied to category_time_scores
```

## 9. Important Rule — Threshold for Using Own Statistics

Enrichment will only use a task's own statistics for future matches when `records >= 3`.  
Until then, Enrichment falls back to:
- `associated_task_statistics_id` (matched task's row)
- OR `category_statistics`

The Stats Recorder naturally enables this threshold by incrementing `records` on every commit.

## 10. Database Tables Reference

| Table | Role in Stats Recorder |
|-------|------------------------|
| `tasks` | Read committed values (`committed_duration`, `committed_difficulty`) |
| `tasks_statistics` | Primary write target — updates via `task_statistics_id` |
| `category_statistics` | Write category-level aggregates (mirrors task behavior) |
| `provisional_schedule` | Read (for Commit and Modify events) |
| `schedule_changes` | Read (for Modify events) |

## 11. Cold Start Behavior

| Field | Default Value |
|-------|---------------|
| `avg_duration` | `NULL` |
| `avg_duration_delta` | `NULL` |
| `avg_difficulty` | `NULL` |
| `avg_difficulty_delta` | `NULL` |
| `completed_count` | `0` |
| `uncompleted_count` | `0` |
| `records` | `0` |
| `location_counts` | `{}` |
| `task_time_scores` | `{}` |
| `category_time_scores` | `{}` |

After the first category completion, category averages begin populating. After `records >= 3`, task-level statistics become the primary enrichment source.

## 12. Implementation Recommendations & Proposals

The following proposals are strongly recommended to ensure reliability, prevent data corruption, and maximize demo-day performance:

| Area | Proposal | Impact |
|------|----------|--------|
| **Execution Mode** | Run Stats Recorder synchronously during MVP. Wrap updates with `SELECT ... FOR UPDATE` if async is required later. | Guarantees mathematical consistency, eliminates race conditions |
| **Denominator Discipline** | Explicitly use `records` for plan averages, `completed_count` for delta averages in all queries. | Maintains mathematical soundness of enrichment pipeline |
| **JSONB Radial Updates** | Compute radial boosts in Python, then apply atomically via `task_time_scores = task_time_scores || %s` | Prevents partial updates and score corruption |
| **Weekly Decay** | Enable `×0.99` weekly normalization as a default cron job | Keeps learning functional, prevents score saturation |
| **Transaction Safety** | Wrap all stats updates in the same DB transaction as the triggering user action | Zero partial-write risk, consistent state on every commit |

## 13. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Update behavioral statistics based on user actions |
| **Trigger Events** | Commit, Completion, Uncompleted, Schedule, Batch Commit, Modify (time), Modify (fields), Delete |
| **Primary Target** | `task_statistics_id` (task's own statistics) |
| **Never Updates** | `associated_task_statistics_id` |
| **Plan Averages Denominator** | `records` (updated on every commit) |
| **Delta Averages Denominator** | `completed_count` (updated only on completion) |
| **Delta Calculation** | `actual - committed`, running average |
| **Completion Tracking** | Fully completed vs fully uncompleted |
| **Time Preference Scores** | Radial decay 0.25/15min, max 10.0, min 0.0 |
| **Learning Signals** | Schedule (+1.0), Commit (+2.0), Modify move (-2.0 original / +1.0 new) |
| **Weekly Decay** | `×0.99` enabled by default (cron) |
| **JSONB Updates** | Python computes → PostgreSQL `||` atomic apply |
| **Execution** | Synchronous for MVP (same transaction as user action) |
| **AI Content** | None — only arithmetic operations |
| **Cold Start** | Default `NULL`/`0`/`{}` until first interaction |
```