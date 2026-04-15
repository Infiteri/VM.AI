# Enrichment Module — Technical Documentation
VM.AI Project · ONIA 2026
Version 4.0 (Stable Pipeline Integration)
Last Updated: April 13, 2026

## 1. Overview

The Enrichment Module is the third stage in the VM.AI pipeline. It receives the parsed task from the NLP Parser and the match result from the Task Matching Model, then enriches the task with historical data, resolves date strings, and computes derived fields like `urgency` and `value`.

### What It Does
- Resolves raw date strings into ISO 8601 datetime objects using `dateparser`
- Applies historical averages from matched tasks or category statistics
- Computes derived fields (`urgency`, `value`) using business formulas
- Creates or locates `tasks_statistics` row
- Inserts task into `tasks` table
- Adds task to `unscheduled_tasks` queue
- Validates fixed-time vs flexible task logic

### What It Does NOT Do
- Parse natural language (handled by NLP Parser)
- Make scheduling decisions (handled by Scheduler)
- Update behavioral statistics (handled by Stats Recorder)
- Process recurring task templates (out of scope)

## 2. Position in Pipeline

```text
NLP Parser → TaskPayload
↓
Task Matching → { name_vector, associated_id, association_status }
↓
Enrichment Module
  ├─ Resolve dates (dateparser)
  ├─ Apply historical averages
  ├─ Compute urgency/value
  ├─ Create tasks_statistics row
  ├─ Insert tasks row
  └─ Add to unscheduled_tasks
↓
Scheduler (if batch triggered)
```

## 3. Key Concepts

| Concept | Description |
|---------|-------------|
| **Data Priority** | Matched task (`records ≥ 3`) → Category stats → Cold start defaults (`0.5`) |
| **Date Resolution** | Strict `dateparser` config: `PREFER_DATES_FROM: future`, `RELATIVE_BASE: now` |
| **Fixed-Time Logic** | Enforces mutual exclusivity: Flexible (start+deadline) OR Fixed (fixed_start) |
| **Draft Pattern** | If from Chat workflow, saves to `task_drafts` instead of main tables |

## 4. Core Formulas

### 4.1 Duration & Difficulty Enrichment
```python
# If matched task has sufficient history (records >= 3)
enriched_duration = matched_stats.avg_duration + matched_stats.avg_duration_delta
enriched_difficulty = matched_stats.avg_difficulty + matched_stats.avg_difficulty_delta

# Else use category statistics
enriched_duration = category_stats.avg_duration.get(difficulty_bucket, default)
enriched_difficulty = category_stats.avg_difficulty

# Cold start fallback
enriched_duration = 60  # Default 1 hour
enriched_difficulty = 0.5  # Default medium
```

### 4.2 Urgency Calculation
```python
days_left = (deadline - now).days
urgency = min(1.0, importance * (1 / max(1, days_left)) * 3)
```

### 4.3 Value Calculation
```python
completion_rate = completed_count / max(1, records)
value = (importance * 0.4 + urgency * 0.4 + difficulty * 0.2) * completion_rate
```

## 5. Date Parsing

### 5.1 Strict Configuration
```python
import dateparser

def parse_strict(raw: str) -> datetime | None:
    return dateparser.parse(raw, settings={
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": datetime.now(),
        "TIMEZONE": "UTC"
    })
```

### 5.2 Validation Rules
- **Flexible Task** (`fixed_time = false`):
  - `start` and `deadline` must be NOT NULL.
  - `fixed_start` must be NULL.
- **Fixed-Time Task** (`fixed_time = true`):
  - `start` and `deadline` must be NULL.
  - `fixed_start` must be NOT NULL.

## 6. Database Writes

### 6.1 `tasks_statistics` Creation
- Creates new row if `association_status = "none"` or `"similar"`
- Reuses existing row if `association_status = "same"`
- Inserts `task_name`, `task_name_vector`, initial counters (`records=0`, `completed_count=0`)

### 6.2 `tasks` Insertion
- Inserts all enriched fields
- Links `task_statistics_id` and `associated_task_statistics_id`
- Sets `rated = false` by default

### 6.3 `unscheduled_tasks` Insertion
- Adds `task_id` to queue for scheduling
- Sets `created_at` for FIFO ordering

### 6.4 `task_drafts` (Chat Workflow Only)
- Stores full task payload + hidden vectors in JSONB
- Returns `draft_id` to frontend
- Auto-deleted after 24 hours if not committed

## 7. Decision Tree

```text
If association_status = "same" AND records >= 3:
    Use matched task's statistics row
Elif association_status = "similar" AND matched records >= 3:
    Use matched task's statistics row for deltas, category for base
Else:
    Use category_statistics only
```

## 8. Cold Start Behavior

| Field | Default Value |
|-------|---------------|
| `avg_duration` | `60` minutes |
| `avg_difficulty` | `0.5` |
| `urgency` | Computed from importance + days_left |
| `value` | Computed from formula |
| `location` | `"Home"` (fallback) |
| `category` | `["personal"]` (fallback) |

After the first category completion, category averages begin populating. After `records >= 3`, task-level statistics become the primary enrichment source.

## 9. Implementation Recommendations & Proposals

| Area | Proposal | Impact |
|------|----------|--------|
| **Pydantic Validation** | Enforce strict schema between NLP output and Enrichment input. | Catches 80% of silent pipeline breaks before math operations |
| **Date String Normalization** | Strip trailing punctuation/whitespace before dateparser. | Prevents ambiguity on messy user input |
| **Fallback Defaults** | Keep safe defaults for all fields if enrichment fails. | Guarantees system never shows "500 Error" to users |
| **Logging** | Log `ENRICHED`, `ENRICHMENT_DURATION_MS` at request boundaries. | Enables real-time debugging during live demos |
| **Fixed-Time Validation** | Use `@model_validator` to enforce mutual exclusivity. | Prevents invalid task states in database |

## 10. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Replace NLP estimates with historical data when reliable |
| **Data Priority** | Matched task (`records ≥ 3`) → Category stats → Cold start defaults |
| **Core Formulas** | `urgency = min(1.0, importance × (1/days_left) × 3)`<br>`value = (imp×0.4 + urg×0.4 + diff×0.2) × completion_rate` |
| **Date Parsing** | Strict `dateparser` config: `PREFER_DATES_FROM: future`, `RELATIVE_BASE: now` |
| **DB Writes** | Creates/locates `tasks_statistics`, inserts `tasks` row, adds to `unscheduled_tasks` |
| **Validation** | Enforces fixed-time vs flexible task logic |
| **Cold Start** | Works immediately. Relies on category defaults. |
| **Execution** | Synchronous, lightweight (`<50ms` end-to-end) |
| **Next Stage** | Scheduler (if batch triggered) or Stats Recorder (on commit) |
