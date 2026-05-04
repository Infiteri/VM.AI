```markdown
# VM.AI — Database Schema Documentation
Version 1.8 · Competition-Ready  
Last Updated: April 5, 2026

## 1. Overview

The VM.AI database consists of three logical groups: **Core Tables** (task storage & scheduling), **Workflow Tables** (task queue & change tracking), and **Statistics Tables** (behavioral learning data). Statistics tables are updated by the Stats Recorder and read by Enrichment, Task Matching, and Scheduler. Core tables are managed by the application workflow.

### Key Constraints
- **Single-user system** — no `user_id` fields anywhere
- **No status field** — task state is derived from presence in `unscheduled_tasks`, `provisional_schedule`, or `scheduled_slots`
- **10-day rolling storage window** — scheduled tasks are kept for 3 past days, current day, and 6 future days. Tasks outside this window are archived/read-only.
- **Recurring tasks** — `NOT IMPLEMENTED` (documented for future scope only)
- **Statistics persistence** — `tasks_statistics` rows are NEVER cascade-deleted when a task is deleted. They persist for historical matching and future `"same"` associations.

## 2. Design Principles

| Principle | Implementation |
|-----------|----------------|
| **One statistics row per task** | Created at task creation time. May be shared if `association_status = "same"`. |
| **Two-link statistics design** | `tasks.task_statistics_id` → this task's own stats. `tasks.associated_task_statistics_id` → matched task's stats (nullable). |
| **Strict cascade boundaries** | Core tables cascade to each other. Statistics tables have `ON DELETE NO ACTION`. |
| **Atomic workflow operations** | Schedule commit, task creation, and stats updates run inside explicit transactions. |
| **Immutable executed tasks** | Tasks with `end < NOW()` or outside the 10-day window cannot be modified or rescheduled. |

## 3. Table Map

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CORE TABLES                                        │
├─────────────────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│           tasks             │  │ scheduled_slots │  │  provisional_schedule│  │
│                             │  │                 │  │                     │  │
│ • id (PK)                   │◄─│ • task_id (FK)  │  │ • task_id (FK)      │  │
│ • task_statistics_id (FK)   │  │ • start         │  │ • start             │  │
│ • associated_task_stats_id  │  │ • end           │  │ • end               │  │
│   (FK, nullable)            │  │ • value         │  │ • value             │  │
│ • created_at, updated_at    │  │ • fixed         │  │ • fixed             │  │
│ • name, start, deadline     │  │ • location      │  │ • location          │  │
│ • difficulty, duration      │  └─────────────────┘  └──────────┬──────────┘  │
│ • category, location        │                                   │             │
│ • importance, urgency, value│                    ┌─────────────────┐           │
│ • fixed_time, fixed_start   │                    │schedule_changes │           │
│ • recurrent (unused)        │                    │ • task_id (FK)  │◄──────────┘
│ • recurrence_days (unused)  │                    │ • change_type   │
└──────────────┬──────────────┘                    │ • old_slot_*    │
               │                                   │ • new_slot_*    │
               ▼                                   │ • created_at    │
┌─────────────────────────────────────────────────┐└─────────────────┘
│                         STATISTICS TABLES        │
├─────────────────────────────┐  ┌────────────────┴┤
│     tasks_statistics        │  │category_statistics│
│ • id (PK)                   │  │ • category_id (PK)│
│ • task_name, vector         │  │ • category_name   │
│ • avg_duration, delta       │  │ • avg_duration (JSONB) │
│ • avg_difficulty, delta     │  │ • avg_duration_delta (JSONB) │
│ • completed/uncompleted_cnt │  │ • avg_difficulty  │
│ • records                   │  │ • avg_difficulty_delta │
│ • location_counts (JSONB)   │  │ • completed/uncompleted_cnt │
│ • task_time_scores (JSONB)  │  │ • records         │
└─────────────────────────────┘  │ • location_counts (JSONB) │
                                 │ • category_time_scores (JSONB) │
┌─────────────────────────────┐  └─────────────────────────────────┘
│     unscheduled_tasks       │
│ • task_id (PK, FK→tasks.id) │
│ • created_at (FIFO order)   │
└─────────────────────────────┘
```

## 4. Core Tables

### 4.1 `tasks` — Primary Task Storage
Source of truth for all task definitions.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `task_statistics_id` | `UUID` | FK → `tasks_statistics.id` (this task's own stats) |
| `associated_task_statistics_id` | `UUID` | FK → `tasks_statistics.id` (matched task's stats) — nullable |
| `created_at`, `updated_at` | `TIMESTAMP` | Audit timestamps |
| `name` | `TEXT` | Task name |
| `start`, `deadline` | `TIMESTAMP` | User's temporal constraints |
| `difficulty`, `duration` | `FLOAT`, `INTEGER` | `0.0–1.0`, minutes |
| `category` | `TEXT[]` | Primary category is first element |
| `location` | `TEXT` | Where task is done |
| `importance`, `urgency`, `value` | `FLOAT` | `0.0–1.0`, computed at enrichment/scheduling |
| `fixed_time` | `BOOLEAN` | Bypasses scoring if `true` |
| `fixed_start` | `TIMESTAMP` | Exact start time (if `fixed_time = true`) |
| `recurrent`, `recurrence_days` | `BOOLEAN`, `TEXT[]` | ⚠ `NOT IMPLEMENTED` — future scope |

**Cascade Rule:** `ON DELETE CASCADE` to `scheduled_slots`, `provisional_schedule`, `schedule_changes`, `unscheduled_tasks`. `ON DELETE NO ACTION` to `tasks_statistics`.

### 4.2 `scheduled_slots` — Main Schedule
Committed, real calendar. Source of truth for what the user sees.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `task_id` | `UUID` | FK → `tasks.id ON DELETE CASCADE` |
| `start`, `end` | `TIMESTAMP` | Slot boundaries |
| `value` | `FLOAT` | Task value at scheduling time |
| `fixed` | `BOOLEAN` | If `true`, cannot be displaced |
| `location` | `TEXT` | For location continuity boost |

### 4.3 `provisional_schedule` — Working Copy
Same schema as `scheduled_slots`. Used by Scheduler to stage changes before commit.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `task_id` | `UUID` | FK → `tasks.id ON DELETE CASCADE` |
| `start`, `end` | `TIMESTAMP` | Slot boundaries |
| `value` | `FLOAT` | Task value |
| `fixed` | `BOOLEAN` | If `true`, cannot be displaced |
| `location` | `TEXT` | For location continuity boost |

### 4.4 `schedule_changes` — Change Log
Records only `insert` and `move` operations applied to transform Main → Provisional.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `task_id` | `UUID` | FK → `tasks.id ON DELETE CASCADE` |
| `change_type` | `VARCHAR(20)` | `'insert'` or `'move'` |
| `old_slot_start`, `old_slot_end` | `TIMESTAMP` | For `move` operations |
| `new_slot_start`, `new_slot_end` | `TIMESTAMP` | For `insert`/`move` |
| `created_at` | `TIMESTAMP` | When change was recorded |

## 5. Workflow Table

### 5.1 `unscheduled_tasks` — Task Queue
Stores only IDs of tasks created/modified but not yet placed into any schedule.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `UUID` | Primary key, FK → `tasks.id ON DELETE CASCADE` |
| `created_at` | `TIMESTAMP` | Used for FIFO ordering in batch scheduling |

## 6. Statistics Tables

### 6.1 `tasks_statistics` — Task-Level Behavioral Data
Updated by Stats Recorder. Read by Enrichment, Task Matching, Scheduler.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `task_name` | `TEXT` | Current task name |
| `task_name_vector` | `FLOAT[]` | 384-dim semantic embedding (used for matching) |
| `avg_duration` | `INTEGER` | Running average of committed duration |
| `avg_duration_delta` | `INTEGER` | Running average of `(actual - committed)` |
| `avg_difficulty` | `FLOAT` | Running average of committed difficulty |
| `avg_difficulty_delta` | `FLOAT` | Running average of `(actual - committed)` |
| `completed_count` | `INTEGER` | Successful completions |
| `uncompleted_count` | `INTEGER` | Failed/cancelled completions |
| `records` | `INTEGER` | Total commits (creation + modifications) |
| `location_counts` | `JSONB` | `{"library": 8, "home": 4}` |
| `task_time_scores` | `JSONB` | `{"10:00": 2.5, "10:15": 1.75}` |

> ⚠️ **Shared Row Invariant:** When `association_status = "same"`, both `tasks.task_statistics_id` and `tasks.associated_task_statistics_id` point to this same row. No new row is created for subsequent matches.

### 6.2 `category_statistics` — Category-Level Behavioral Data
Pre-seeded with: `study (1)`, `fitness (2)`, `work (3)`, `personal (4)`.

| Field | Type | Description |
|-------|------|-------------|
| `category_id` | `INTEGER` | Primary key |
| `category_name` | `TEXT` | Category label |
| `avg_duration` | `JSONB` | Keyed by difficulty bucket: `{"0.5": 35, "1.0": 55}` |
| `avg_duration_delta` | `JSONB` | Keyed by difficulty bucket |
| `avg_difficulty` | `FLOAT` | Single value per category |
| `avg_difficulty_delta` | `FLOAT` | Single value per category |
| `completed_count`, `uncompleted_count`, `records` | `INTEGER` | Category-level counters |
| `location_counts` | `JSONB` | `{"home": 8, "library": 4}` |
| `category_time_scores` | `JSONB` | `{"10:00": 1.8, "14:00": 2.2}` |

## 7. Relationships & Cascade Rules

| From Table | To Table | Relationship | Foreign Key | Cascade on Delete |
|------------|----------|--------------|-------------|-------------------|
| `tasks` | `tasks_statistics` | Many-to-one | `task_statistics_id` | `NO ACTION` |
| `tasks` | `tasks_statistics` | Many-to-one | `associated_task_statistics_id` | `NO ACTION` |
| `tasks` | `scheduled_slots` | One-to-many | `task_id` | `CASCADE` |
| `tasks` | `provisional_schedule` | One-to-many | `task_id` | `CASCADE` |
| `tasks` | `schedule_changes` | One-to-many | `task_id` | `CASCADE` |
| `tasks` | `unscheduled_tasks` | One-to-one | `id = task_id` | `CASCADE` |

## 8. Recommended Indexes (Performance)

Add these immediately after schema creation to guarantee sub-second overlap checks and FIFO ordering:

```sql
-- Overlap checks for Scheduler (provisional & committed)
CREATE INDEX idx_provisional_range ON provisional_schedule (start, end);
CREATE INDEX idx_scheduled_range ON scheduled_slots (start, end);

-- FIFO ordering for batch scheduling
CREATE INDEX idx_unscheduled_fifo ON unscheduled_tasks (created_at);

-- Semantic matching acceleration (optional but recommended)
CREATE INDEX idx_stats_name ON tasks_statistics (task_name);
```

## 9. Implementation Recommendations & Proposals

The following proposals are strongly recommended to ensure data integrity, prevent corruption, and maximize demo-day reliability:

| Area | Proposal | Impact |
|------|----------|--------|
| **Atomic Schedule Commit** | Wrap `provisional_schedule → scheduled_slots` copy in a single transaction: `BEGIN` → `DELETE FROM scheduled_slots` → `INSERT ... SELECT` → `TRUNCATE schedule_changes` → `COMMIT` | Prevents blank calendar on network drop or server restart |
| **Shared Statistics Row Safety** | Add `reference_count INTEGER DEFAULT 1` to `tasks_statistics`. Increment on `"same"` match, decrement on delete. Only allow cleanup when `= 0` | Prevents orphaned or prematurely reused statistics rows |
| **Synchronous Stats for MVP** | Run Stats Recorder in the same request/transaction as completion/commit. Use `SELECT ... FOR UPDATE` on stats rows if async is required later | Guarantees mathematical consistency, eliminates race conditions |
| **JSONB Radial Updates** | Compute radial boosts in Python, then apply atomically: `UPDATE ... SET task_time_scores = task_time_scores || %s WHERE id = %s` | Prevents partial updates and score corruption |
| **Weekly Decay Job** | Enable `×0.99` weekly normalization via cron: `UPDATE ... SET task_time_scores = jsonb_object_agg(key, GREATEST(0, LEAST(10, value * 0.99)))` | Keeps learning functional, prevents score saturation |
| **Denominator Discipline** | Explicitly use `records` for plan averages, `completed_count` for delta averages in all queries. Document in code comments. | Maintains mathematical soundness of enrichment pipeline |

## 10. Summary Table

| Table | Purpose | Written By | Read By |
|-------|---------|------------|---------|
| `tasks` | Primary task storage | Enrichment, Modify operations | Scheduler, Stats Recorder, UI |
| `scheduled_slots` | Main committed schedule | Commit operation (transactional) | UI, Scheduler (displacement context) |
| `provisional_schedule` | Working copy before commit | Scheduler (batch run) | Scheduler, UI (Pending Changes) |
| `schedule_changes` | Change log (insert/move only) | Scheduler | UI (Pending Changes Page) |
| `unscheduled_tasks` | Task IDs waiting for scheduling | Enrichment, Modify operations | Scheduler (FIFO queue) |
| `tasks_statistics` | Task-level behavioral data | Stats Recorder | Enrichment, Task Matching, Scheduler |
| `category_statistics` | Category-level aggregates | Stats Recorder | Enrichment, Scheduler |

---
*Document prepared for ONIA 2026. All schemas, indexes, and cascade rules are aligned with competition deadlines and 1-month implementation constraints.*
```