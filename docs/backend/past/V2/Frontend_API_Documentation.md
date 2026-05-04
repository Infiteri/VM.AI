```markdown
# VM.AI — Frontend API Documentation
**Version:** 2.2 (Final Build)  
**Competition:** ONIA 2026  
**Base URL:** `http://localhost:8000/api/v1`  
**Last Updated:** April 6, 2026

---

## Table of Contents
1. [Overview & Conventions](#overview--conventions)
2. [Error Handling](#error-handling)
3. [Main Schedule Endpoints](#main-schedule-endpoints)
4. [Task Management Endpoints](#task-management-endpoints)
5. [Pending Changes & Scheduling Endpoints](#pending-changes--scheduling-endpoints)
6. [Data Models & Context Reference](#data-models--context-reference)

---

## Overview & Conventions

- **Authentication:** Not implemented for MVP (single-user system)
- **Timestamps:** ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`)
- **UUIDs:** Standard format (`550e8400-e29b-41d4-a716-446655440000`)
- **State Derivation:** Tasks have no `status` field. State is inferred from table presence:
  - `unscheduled_tasks` → awaiting scheduling
  - `provisional_schedule` → staged for commit
  - `scheduled_slots` → committed main schedule

---

## Error Handling

All errors return a consistent JSON structure:
```json
{
  "detail": "Error message description",
  "error_code": "ERROR_TYPE",
  "timestamp": "2026-04-06T10:30:00"
}
```

### Common HTTP Status Codes
| Code | Meaning |
|------|---------|
| `200` | Successful request |
| `201` | Resource created successfully |
| `204` | Successful deletion |
| `400` | Invalid input data |
| `404` | Resource not found |
| `409` | Task already rated or scheduled |
| `422` | Validation error |
| `500` | Server-side error |

---

## Main Schedule Endpoints

### 1. Get Schedule for Date
**`GET /schedule?date={YYYY-MM-DD}`**

Retrieves all committed tasks for a specific date from `scheduled_slots`.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Yes | Date in `YYYY-MM-DD` format |

**Response:**
```json
{
  "date": "2026-04-06",
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Math Homework",
      "start": "2026-04-06T08:00:00",
      "end": "2026-04-06T09:00:00",
      "location": "Home",
      "rated": true
    }
  ]
}
```

---

### 2. Rate Task Completion
**`POST /tasks/{task_id}/rate`**

Records completion status and triggers synchronous Stats Recorder update.

**Request Body:**
```json
{
  "completed": true,
  "actual_duration": 55,
  "actual_difficulty": 0.7
}
```
*Note: `actual_duration` and `actual_difficulty` must be omitted if `completed: false`.*

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "stats_updated": true,
  "message": "Task rated successfully"
}
```

**Errors:**
- `409 TASK_ALREADY_RATED` — Task has already been rated
- `422 MISSING_RATING_FIELDS` — Duration/difficulty required when `completed=true`

---

### 3. Delete Task (Unified)
**`DELETE /tasks/{task_id}?source={context}`**

Permanently removes a task based on its current workflow state. Statistics persist.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | `main_schedule`, `unscheduled`, or `provisional` |

**Response:**
```json
{
  "success": true,
  "message": "Task deleted successfully",
  "deleted_from": ["scheduled_slots", "tasks"]
}
```

**Cascade Behavior by Source:**
| Source | Tables Affected |
|--------|-----------------|
| `main_schedule` | `scheduled_slots`, `tasks` |
| `unscheduled` | `unscheduled_tasks` only |
| `provisional` | `provisional_schedule`, `schedule_changes` |

---

## Task Management Endpoints

### 4. Parse Modification Prompt
**`POST /tasks/parse/modify`**

Uses NLP Parser to interpret natural language edit requests. Returns updated fields for form pre-fill.

**Request:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "prompt": "make it 2 hours and move to afternoon"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "enriched_task": {
    "name": { "value": "Math Homework", "predicted": false },
    "duration": { "value": 120, "predicted": true },
    "deadline": { "value": "2026-04-07T23:59:00", "predicted": false },
    "difficulty": { "value": 0.6, "predicted": true },
    "location": { "value": "Home", "predicted": false },
    "category": { "value": ["study"], "predicted": false },
    "fixed_time": { "value": false, "predicted": false },
    "importance": { "value": 0.7, "predicted": true }
  }
}
```

---

### 5. Submit Modified Task
**`POST /tasks/{task_id}/update?source={context}`**

Submits a fully modified task. Removes old task from schedule, creates new version in `unscheduled_tasks`.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | `main_schedule`, `unscheduled`, or `provisional` |

**Request:**
```json
{
  "task": {
    "name": { "value": "Math Homework", "predicted": false },
    "duration": { "value": 120, "predicted": true },
    "deadline": { "value": "2026-04-07T23:59:00", "predicted": false },
    "difficulty": { "value": 0.6, "predicted": true },
    "location": { "value": "Home", "predicted": false },
    "category": { "value": ["study"], "predicted": false },
    "fixed_time": { "value": false, "predicted": false },
    "importance": { "value": 0.7, "predicted": true }
  }
}
```

**Response:**
```json
{
  "success": true,
  "new_task_id": "550e8400-e29b-41d4-a716-446655440099",
  "old_task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "unscheduled"
}
```

---

### 6. Parse New Task (Add Mode)
**`POST /tasks/parse/add`**

Extracts task fields from natural language input for initial form population.

**Request:**
```json
{
  "prompt": "finish chemistry homework before Friday, pretty hard, about 90 minutes"
}
```

**Response:**
```json
{
  "enriched_task": {
    "name": { "value": "Chemistry Homework", "predicted": false },
    "deadline": { "value": "2026-04-10", "predicted": false },
    "difficulty": { "value": 0.8, "predicted": false },
    "duration": { "value": 90, "predicted": false },
    "category": { "value": ["study"], "predicted": true },
    "location": { "value": "Home", "predicted": true },
    "fixed_time": { "value": false, "predicted": false },
    "importance": { "value": 0.6, "predicted": true }
  }
}
```

---

### 7. Create New Task
**`POST /tasks`**

Creates a new task in the database and adds it to `unscheduled_tasks`.

**Request:**
```json
{
  "task": {
    "name": { "value": "Chemistry Homework", "predicted": false },
    "duration": { "value": 90, "predicted": true },
    "deadline": { "value": "2026-04-10T23:59:00", "predicted": false },
    "difficulty": { "value": 0.8, "predicted": true },
    "location": { "value": "Home", "predicted": true },
    "category": { "value": ["study"], "predicted": true },
    "fixed_time": { "value": false, "predicted": false },
    "importance": { "value": 0.6, "predicted": true }
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "unscheduled",
  "created_at": "2026-04-06T10:30:00"
}
```

---

## Pending Changes & Scheduling Endpoints

### 8. Get Unscheduled Tasks Queue
**`GET /unscheduled?limit={number}`**

Retrieves all tasks waiting to be scheduled, ordered by `created_at` (FIFO).

**Response:**
```json
{
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "name": "Chemistry Homework",
      "duration": 90,
      "deadline": "2026-04-10T23:59:00",
      "difficulty": 0.8,
      "location": "Home",
      "category": ["study"],
      "fixed_time": false,
      "fixed_start": null,
      "importance": 0.6,
      "urgency": 0.45,
      "value": 0.62,
      "created_at": "2026-04-06T10:30:00"
    }
  ],
  "total_count": 1
}
```

---

### 9. Schedule Batch Tasks
**`POST /schedule/batch`**

Triggers the Stable Incremental Scheduler. Reads all IDs from `unscheduled_tasks`, places feasible tasks into `provisional_schedule`, logs changes, and removes scheduled tasks from the queue.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "scheduled_count": 2,
  "unscheduled_remaining": [],
  "message": "All tasks scheduled successfully",
  "provisional_changes": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "task_name": "Chemistry Homework",
      "change_type": "insert",
      "new_slot_start": "2026-04-06T16:00:00",
      "new_slot_end": "2026-04-06T17:30:00",
      "location": "Home"
    }
  ],
  "execution_time_ms": 1250
}
```

---

### 10. Get Provisional Schedule Changes
**`GET /provisional/changes`**

Retrieves all pending inserts/moves in the working schedule.

**Response:**
```json
{
  "changes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440100",
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "task_name": "Chemistry Homework",
      "change_type": "insert",
      "old_slot_start": null,
      "old_slot_end": null,
      "new_slot_start": "2026-04-06T16:00:00",
      "new_slot_end": "2026-04-06T17:30:00",
      "location": "Home",
      "value": 0.62,
      "fixed": false,
      "created_at": "2026-04-06T12:00:00"
    }
  ],
  "total_count": 1
}
```

---

### 11. Reset Provisional to Main Schedule
**`POST /provisional/reset`**

Discards all provisional changes and resets working copy to match committed schedule.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "message": "Provisional schedule reset to main schedule",
  "changes_discarded": 2
}
```

---

### 12. Commit Provisional Schedule
**`POST /provisional/commit`**

Atomically copies `provisional_schedule` to `scheduled_slots` and clears change logs. Wrapped in PostgreSQL transaction.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "committed_count": 5,
  "message": "Schedule committed successfully",
  "transaction_time_ms": 45
}
```

---

## Data Models & Context Reference

### Task Object with Predicted Flags
Used in `POST /tasks` and `POST /tasks/{id}/update` requests.
```json
{
  "name": { "value": "string", "predicted": "boolean" },
  "duration": { "value": "integer", "predicted": "boolean" },
  "deadline": { "value": "string (ISO 8601)", "predicted": "boolean" },
  "difficulty": { "value": "float (0.0-1.0)", "predicted": "boolean" },
  "location": { "value": "string", "predicted": "boolean" },
  "category": { "value": "array of strings", "predicted": "boolean" },
  "fixed_time": { "value": "boolean", "predicted": "boolean" },
  "importance": { "value": "float (0.0-1.0)", "predicted": "boolean" }
}
```

### Source Context Values
| Value | Meaning |
|-------|---------|
| `main_schedule` | Task is in committed `scheduled_slots` |
| `unscheduled` | Task is in queue waiting for scheduling |
| `provisional` | Task is in working copy pending commit |

### Predicted Flag Logic
- `predicted: false` → User stated explicitly. Backend will never override.
- `predicted: true` → Model estimated. Backend may replace with historical data during enrichment.

---
**Document prepared for ONIA 2026. All endpoints align with Database Schema v1.8, 5-stage pipeline, and synchronous MVP constraints.**
```