# Scheduling Engine — Technical Documentation
VM.AI Project · ONIA 2026
Version 4.0 (Stable Incremental Scheduler)

## 1. Overview

The Scheduling Engine is the fourth stage in the VM.AI pipeline. It takes enriched tasks from the `unscheduled_tasks` table and determines optimal calendar slots using a **stability-first incremental approach**.

### Key Design Principles
- **Schedule stability over global optimality**: Minimize changes to existing provisional schedule
- **Predictable complexity**: Bounded `O(N × 15)` instead of exponential displacement chains
- **User trust**: Tasks don't jump around unnecessarily; changes are intentional and value-driven

### What It Does
- Reads enriched tasks from `tasks` table (using task IDs from `unscheduled_tasks`)
- Reads current calendar state from `provisional_schedule`
- Eliminates impossible slots (Constraint Solver)
- Scores remaining slots using a deterministic formula with **stability penalty**
- Selects highest-scored slot with **1-layer displacement max** and **25% value threshold**
- Writes changes to `provisional_schedule` and `schedule_changes`

### What It Does NOT Do
- Rewrite the entire schedule for marginal improvements
- Displace tasks unless the new task is significantly more valuable (≥25%)
- Chain displacements beyond 1 layer
- Modify user behavioral profile or time preference scores

## 2. Position in Pipeline

```
User clicks "Schedule Tasks" on Pending Changes Page
↓
Scheduler reads unscheduled_tasks (gets task_id list, FIFO order)
↓
Scheduler reads task data from tasks table using task_id
↓
For each task:
  Constraint Solver → eliminates impossible slots
  Top-15 Candidate Pruning → fast pre-ranking
  Slot Ranker → scores top 15 candidates with stability penalty
  Displacement Handler → resolves conflicts (max 1 layer, 25% threshold)
  Write changes to provisional_schedule + schedule_changes
↓
Remove task_id from unscheduled_tasks
↓
Display changes in Schedule Changes List
↓
User reviews, modifies, or commits
↓
Stats Recorder updates time preference scores
```

## 3. Key Concepts

| Concept | Description |
|---------|-------------|
| Unscheduled Tasks | Task IDs of tasks created/modified but not yet placed. Stored in `unscheduled_tasks`. |
| Main Schedule | Real, committed calendar. Source of truth. Stored in `scheduled_slots`. |
| Provisional Schedule | Working copy where scheduled changes are applied before commit. Stored in `provisional_schedule`. |
| Schedule Changes | Log of changes (insert, move) applied to transform Main → Provisional. Stored in `schedule_changes`. |
| Stability Penalty | Score deduction applied when a candidate slot is already occupied. Prevents schedule thrashing. |
| Scheduling Horizon | 7-day rolling window. |

## 4. Stable Incremental Scheduling Algorithm

The engine processes tasks in FIFO order. For each task, it runs the following deterministic steps:

### 4.1 Constraint Solver (Elimination)
Removes truly impossible slots before scoring:
1. Remove slots ending after the task's deadline
2. Remove slots shorter than the task's duration
3. Remove slots occupied by fixed tasks (`fixed = true`)

What remains: free slots + slots occupied by non-fixed tasks (displacement handles these).

### 4.2 Top-15 Candidate Pruning
Instead of scoring all 672 possible 15-minute slots:
1. Fast pre-rank remaining slots using `base_score + time_preference_boost`
2. Keep only the **top 15 candidates**
3. Run full feasibility, location, and stability checks only on those 15

### 4.3 Stable Scoring Formula
```text
slot_score = base_score
           + free_slot_boost
           - stability_penalty
           + location_continuity_boost
           + overlap_penalty
           + time_preference_boost
```

### 4.4 Displacement Logic (Updated)
When the highest-scored candidate is occupied by a non-fixed task:
1. **Value Threshold Check**: `if new_task.value < existing_task.value * 1.25 → skip slot`
2. **Max 1 Layer**: Displace at most one task per scheduling run. Once a task is moved, it becomes `fixed=True` for the remainder of the batch.
3. **Feasibility Check**: Verify the displaced task has at least one valid slot remaining before its own deadline.
4. **Fallback**: If feasibility fails, skip to the next candidate.

## 5. Slot Ranker — Scoring Components

| Component | Value | Description |
|-----------|-------|-------------|
| `base_score` | `(importance × 0.4) + (urgency × 0.4) + (difficulty × 0.2)` | Core task value. Range: `0.0–1.0`. |
| `free_slot_boost` | `+0.15` if free, `0.0` if occupied | Prefers empty slots. |
| `stability_penalty` | `0.0` if free, `-0.50` if occupied | Strongly discourages moving existing tasks. |
| `location_continuity_boost` | `+0.10` per adjacent matching location (max `+0.20`) | Encourages grouping same-location tasks. |
| `overlap_penalty` | `-0.05` per overlapping task | Penalizes crowded slots. |
| `time_preference_boost` | Lookup from `task_time_scores` or `category_time_scores` (max `10.0`) | User's historical preference. Additive. |

> 💡 `free_slot_boost` and `stability_penalty` are mutually exclusive. They share the same occupancy check:
> ```python
> if is_occupied:
>     score += 0.00   # free_slot_boost
>     score -= 0.50   # stability_penalty
> else:
>     score += 0.15   # free_slot_boost
>     score -= 0.00   # stability_penalty
> ```

## 6. Time Preference Scores — Learning from User Behaviour

Maintained by the Stats Recorder. Used during scoring to boost slots matching historical preferences.

| Parameter | Value |
|-----------|-------|
| Granularity | 15-minute intervals |
| Max score per slot | 10.0 |
| Min score per slot | 0.0 |
| Lookup priority | Task-level → Category-level → 0.0 |
| Decay | Radial: `boost = base × (1 - blocks × 0.25)`, min 0.0 |

Events that update scores (handled by Stats Recorder):
- Schedule: `+1.0`
- Commit: `+2.0` (per task)
- Move: `-2.0` original slot, `+1.0` new slot

## 7. Task Types

| Type | Behavior |
|------|----------|
| **Standard Flexible** (`fixed_time: false`) | Runs full pipeline. Subject to stability scoring and displacement rules. |
| **Fixed-Time** (`fixed_time: true`) | Bypasses scoring. Inserts directly at `fixed_start`. Displaces lower-value tasks only if `value × 1.25` threshold met. |
| **Recurring** | ⚠ NOT IMPLEMENTED — future scope only. |

## 8. Batch Scheduling & Execution

When the user clicks "Schedule Tasks":
1. Read all task IDs from `unscheduled_tasks`, ordered by `created_at` (FIFO)
2. For each task, run the stable scheduling algorithm
3. Apply changes to `provisional_schedule` and log to `schedule_changes`
4. Remove task ID from `unscheduled_tasks`
5. **Hard Timeout**: `12 seconds` max per batch. Returns best feasible schedule found.
6. **Early Termination**: If `best_score < 0.35` after evaluating candidates, leave task unscheduled and proceed to next.
7. If a task cannot be placed, it remains in `unscheduled_tasks` and the user is notified.

## 9. Data Sources

| Source | Table/Field | Purpose |
|--------|-------------|---------|
| Enriched Task | `tasks` (via `unscheduled_tasks`) | duration, deadline, value, category, location, fixed_time, task_statistics_id |
| Working Schedule | `provisional_schedule` | start, end, value, fixed, location (for overlap & continuity checks) |
| Time Preferences | `tasks_statistics.task_time_scores`<br>`category_statistics.category_time_scores` | Additive boost during scoring |
| Computed Internally | — | candidate slots, slot_score, fixed_end, occupancy flags |

## 10. Cold Start Behaviour

When a user has no history, the engine works immediately:
- `time_preference_boost` defaults to `0.0`
- `location_continuity_boost` works based on actual locations in the provisional schedule
- Displacement works based on task values from Enrichment
- System learns preferences organically as tasks are scheduled, committed, and rated.

## 11. Implementation Recommendations & Proposals

The following proposals are strongly recommended to ensure reliability, prevent data corruption, and maximize demo-day performance:

| Area | Proposal | Impact |
|------|----------|--------|
| **Commit Atomicity** | Wrap `provisional_schedule → scheduled_slots` copy in a single PostgreSQL transaction using `BEGIN` / `INSERT ... SELECT` / `COMMIT` | Prevents blank calendar on network drop or server restart |
| **Stats Execution Mode** | Run Stats Recorder synchronously during MVP. Wrap `tasks_statistics` updates with `SELECT ... FOR UPDATE` if async is required later | Guarantees mathematical consistency, eliminates race conditions |
| **NLP Boundary Validation** | Add Pydantic schema validation between NLP output and Enrichment input. Reject/fix type mismatches early | Catches 80% of silent pipeline breaks before they reach the scheduler |
| **Database Indexes** | Create indexes: `idx_provisional_range (start, end)`, `idx_scheduled_range (start, end)`, `idx_unscheduled_fifo (created_at)` | 10–50x faster overlap checks and FIFO ordering |
| **Date Parsing Safety** | Configure `dateparser` with `PREFER_DATES_FROM: future`, `RELATIVE_BASE: now()` | Eliminates ambiguous "Friday" vs "last Friday" misinterpretations |
| **JSONB Radial Updates** | Compute radial boosts in Python, then apply atomically via `task_time_scores = task_time_scores || %s` | Prevents partial updates and score corruption |
| **Denominator Discipline** | Explicitly use `records` for plan averages, `completed_count` for delta averages in Stats Recorder formulas | Maintains mathematical soundness of enrichment pipeline |

## 12. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Determine optimal calendar slot for each unscheduled task with stability guarantees |
| **Inputs** | `unscheduled_tasks` (FIFO), `tasks` (enriched data), `provisional_schedule`, time preference scores |
| **Outputs** | `provisional_schedule` updates, `schedule_changes` entries |
| **Algorithm** | Constraint Solver → Top-15 Pruning → Stable Scoring → 1-Layer Displacement |
| **Scoring** | `base_score + free_slot_boost - stability_penalty + location + overlap + time_pref` |
| **Stability Rules** | `-0.50` penalty if occupied, `1.25×` value threshold to displace, moved tasks become `fixed=True` for the run |
| **Execution Guards** | 12s hard timeout, `<0.35` early termination, FIFO ordering, graceful fallback |
| **Time Preference** | Additive, max 10.0, radial decay 0.25/block, lookup task → category → 0.0 |
| **Horizon** | 7-day rolling window |
| **Change Recording** | Insert and move only. Delete is not recorded. |
| **Cold Start** | Works immediately, improves organically as user interacts |
| **Recurring Tasks** | NOT IMPLEMENTED — documented as future scope |