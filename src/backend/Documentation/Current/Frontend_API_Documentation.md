# VM.AI — Frontend API Documentation
**Version:** 3.0 (Strict Validation & Draft Pattern)
**Competition:** ONIA 2026
**Base URL:** `http://localhost:8000/api/v1`
**Last Updated:** April 13, 2026

---

## Table of Contents
1. [Overview & Conventions](#overview--conventions)
2. [Error Handling](#error-handling)
3. [Main Schedule Endpoints](#main-schedule-endpoints)
4. [Task Management Endpoints](#task-management-endpoints)
5. [Pending Changes & Scheduling Endpoints](#pending-changes--scheduling-endpoints)
6. [Data Models & Validation Rules](#data-models--validation-rules)

---

## Overview & Conventions

- **Authentication:** Not implemented for MVP (single-user system)
- **Timestamps:** ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`). All datetime fields are validated strictly.
- **UUIDs:** Standard format (`550e8400-e29b-41d4-a716-446655440000`). All IDs are UUIDs.
- **State Derivation:** Tasks have no `status` field. State is inferred from table presence:
  - `unscheduled_tasks` → awaiting scheduling
  - `provisional_schedule` → staged for commit
  - `main_schedule` → committed main schedule
- **Draft Pattern:** Tasks created via Chat/AI receive a `draft_id`. This ID must be sent back during commit to link the draft to the final task.
- **Validation:** Strict type checking and range validation at the API boundary. Invalid requests return `422` immediately.

---

## Error Handling

All errors return a consistent JSON structure:
```json
{
  "detail": [
    {
      "loc": ["body", "task", "difficulty"],
      "msg": "Input should be less than or equal to 1",
      "type": "less_than_equal"
    }
  ]
}
```

### Common HTTP Status Codes
| Code | Meaning | Example |
|------|---------|---------|
| `200` | Successful request | `POST /tasks/{id}/rate` |
| `201` | Resource created successfully | `POST /tasks` |
| `204` | Successful deletion | `DELETE /tasks/{id}` |
| `404` | Resource not found | Invalid UUID in path |
| `422` | Validation error | Invalid types, missing fields, range violations |
| `500` | Server-side error | Internal failure (logged to `backend.log`) |

---

## Main Schedule Endpoints

### 1. Get Schedule for Date
**`GET /schedule?date={YYYY-MM-DD}`**

Retrieves all committed tasks for a specific date from `main_schedule`.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | date | Yes | Date in `YYYY-MM-DD` format. Validated as strict date type. |

**Response:**
```json
{
  "date": "2026-04-06",
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
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

### 2. Schedule Batch Tasks
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
  "unscheduled_remaining": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "payload": {
        "name": "Chemistry Project",
        "start": "2026-04-19T09:00:00",
        "deadline": "2026-04-20T17:00:00",
        "difficulty": 0.8,
        "duration": 120,
        "category": ["study"],
        "location": "Library",
        "importance": 0.9,
        "fixed_time": false,
        "fixed_start": null
      },
      "created_at": "2026-04-06T10:30:00"
    }
  ],
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

## Task Management Endpoints

### 3. Parse New Task (Add Mode)
**`POST /tasks/parse/add`**

Extracts task fields from natural language input for initial form population. Returns a `draft_id` for later commit.

**Request:**
```json
{
  "prompt": "finish chemistry homework before Friday, pretty hard, about 90 minutes"
}
```

**Response:**
```json
{
  "draft_id": "123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "name": "Chemistry Homework",
    "start": "2026-04-14T09:00:00",
    "deadline": "2026-04-18T23:59:00",
    "difficulty": 0.8,
    "duration": 90,
    "category": ["study"],
    "location": "Home",
    "importance": 0.6,
    "fixed_time": false,
    "fixed_start": null
  }
}
```

---

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
  "task": {
    "name": "Chemistry Homework",
    "start": "2026-04-14T14:00:00",
    "deadline": "2026-04-18T23:59:00",
    "difficulty": 0.8,
    "duration": 120,
    "category": ["study"],
    "location": "Home",
    "importance": 0.6,
    "fixed_time": false,
    "fixed_start": null
  }
}
```

---

### 5. Create New Task (Commit)
**`POST /tasks`**

Creates a new task in the database. Supports two workflows:
- **Case A (Draft Commit):** If `draft_id` is provided, commits the draft from `task_drafts` table.
- **Case B (Manual Creation):** If `draft_id` is omitted, runs direct pipeline (Task Matching → Enrichment → DB).

**Request (Case A - Draft Commit):**
```json
{
  "draft_id": "123e4567-e89b-12d3-a456-426614174000",
  "task": {
    "name": "Chemistry Homework",
    "start": "2026-04-14T09:00:00",
    "deadline": "2026-04-18T23:59:00",
    "difficulty": 0.8,
    "duration": 90,
    "category": ["study"],
    "location": "Home",
    "importance": 0.6,
    "fixed_time": false,
    "fixed_start": null
  }
}
```

**Request (Case B - Manual Creation):**
```json
{
  "task": {
    "name": "Chemistry Homework",
    "start": "2026-04-14T09:00:00",
    "deadline": "2026-04-18T23:59:00",
    "difficulty": 0.8,
    "duration": 90,
    "category": ["study"],
    "location": "Home",
    "importance": 0.6,
    "fixed_time": false,
    "fixed_start": null
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "unscheduled",
  "message": "Task created successfully"
}
```

---

### 6. Get Task Details
**`GET /tasks/{id}`**

Fetches details of a specific task by ID. Used by frontend to populate modification forms.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Task UUID |

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "payload": {
    "name": "Math Homework",
    "start": "2026-04-06T08:00:00",
    "deadline": "2026-04-07T17:00:00",
    "difficulty": 0.7,
    "duration": 60,
    "category": ["study"],
    "location": "Library",
    "importance": 0.8,
    "fixed_time": false,
    "fixed_start": null
  },
  "created_at": "2026-04-05T10:30:00"
}
```

---

### 7. Submit Modified Task
**`POST /tasks/{id}/update?source={context}`**

Submits a fully modified task. Removes old task from schedule, creates new version in `unscheduled_tasks`.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Task UUID to update |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | `main_schedule`, `unscheduled`, or `provisional` |

**Request:**
```json
{
  "task": {
    "name": "Updated Math Homework",
    "start": "2026-04-06T10:00:00",
    "deadline": "2026-04-07T17:00:00",
    "difficulty": 0.6,
    "duration": 90,
    "category": ["study"],
    "location": "Home",
    "importance": 0.7,
    "fixed_time": false,
    "fixed_start": null
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440099",
  "status": "unscheduled",
  "message": "Task updated successfully"
}
```

---

### 8. Delete Task (Unified)
**`DELETE /tasks/{id}?source={context}`**

Permanently removes a task based on its current workflow state. Statistics persist.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Task UUID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | string | Yes | `main_schedule`, `unscheduled`, or `provisional` |

**Response:**
```json
{
  "success": true,
  "message": "Task deleted successfully",
  "deleted_from": ["main_schedule", "tasks"]
}
```

**Cascade Behavior by Source:**
| Source | Tables Affected |
|--------|-----------------|
| `main_schedule` | `main_schedule`, `tasks` |
| `unscheduled` | `unscheduled_tasks` only |
| `provisional` | `provisional_schedule`, `schedule_changes` |

---

### 9. Get Unscheduled Tasks Queue
**`GET /tasks/unscheduled?limit={number}`**

Retrieves all tasks waiting to be scheduled, ordered by `created_at` (FIFO).

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Max number of tasks to return. Default: 50. |

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "payload": {
        "name": "Chemistry Homework",
        "start": "2026-04-19T09:00:00",
        "deadline": "2026-04-20T17:00:00",
        "difficulty": 0.8,
        "duration": 120,
        "category": ["study"],
        "location": "Library",
        "importance": 0.9,
        "fixed_time": false,
        "fixed_start": null
      },
      "created_at": "2026-04-06T10:30:00"
    }
  ],
  "total_count": 1
}
```

---

### 10. Rate Task Completion
**`POST /tasks/{task_id}/rate`**

Records completion status and triggers synchronous Stats Recorder update.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | UUID | Yes | Task UUID |

**Request (Completed):**
```json
{
  "completed": true,
  "actual_duration": 55,
  "actual_difficulty": 0.7
}
```

**Request (Not Completed):**
```json
{
  "completed": false
}
```

**Validation Rules:**
- If `completed = true`: `actual_duration` and `actual_difficulty` are **required**.
- If `completed = false`: `actual_duration` and `actual_difficulty` must be **omitted**.
- `actual_duration`: Integer, range `0 < x < 1440` minutes.
- `actual_difficulty`: Float, range `0.0 < x <= 1.0`.

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "stats_updated": true,
  "message": "Task rated successfully"
}
```

---

## Pending Changes & Scheduling Endpoints

### 11. Get Provisional Schedule Changes
**`GET /provisional/changes`**

Retrieves all pending inserts/moves in the working schedule.

**Response:**
```json
{
  "changes": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "task_name": "Chemistry Homework",
      "change_type": "insert",
      "new_slot_start": "2026-04-06T16:00:00",
      "new_slot_end": "2026-04-06T17:30:00",
      "location": "Home"
    }
  ],
  "total_count": 1
}
```

---

### 12. Reset Provisional to Main Schedule
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

### 13. Commit Provisional Schedule
**`POST /provisional/commit`**

Atomically copies `provisional_schedule` to `main_schedule` and clears change logs. Wrapped in PostgreSQL transaction.

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

## Data Models & Validation Rules

### TaskPayload
Used in `POST /tasks` and `POST /tasks/{id}/update` requests.

```json
{
  "name": "Chemistry Homework",
  "start": "2026-04-14T09:00:00",
  "deadline": "2026-04-18T23:59:00",
  "difficulty": 0.8,
  "duration": 90,
  "category": ["study"],
  "location": "Home",
  "importance": 0.6,
  "fixed_time": false,
  "fixed_start": null
}
```

**Validation Rules:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | Min length: 1 character |
| `start` | datetime | Conditional | Required if `fixed_time = false` |
| `deadline` | datetime | Conditional | Required if `fixed_time = false` |
| `difficulty` | float | Yes | `0.0 < x <= 1.0` |
| `duration` | integer | Yes | `0 < x < 1440` minutes |
| `category` | array[string] | Yes | Min items: 1 |
| `location` | string | Yes | Cannot be empty |
| `importance` | float | Yes | `0.0 < x <= 1.0` |
| `fixed_time` | boolean | No | Default: false |
| `fixed_start` | datetime | Conditional | Required if `fixed_time = true` |

**Logic Constraints:**
- **Flexible Task** (`fixed_time = false`):
  - `start` and `deadline` must be NOT NULL.
  - `fixed_start` must be NULL.
- **Fixed-Time Task** (`fixed_time = true`):
  - `start` and `deadline` must be NULL.
  - `fixed_start` must be NOT NULL.

### TaskDetailResponse
Used in `GET /tasks/{id}` and `GET /tasks/unscheduled` responses.

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440001",
  "payload": {
    "name": "Math Homework",
    "start": "2026-04-06T08:00:00",
    "deadline": "2026-04-07T17:00:00",
    "difficulty": 0.7,
    "duration": 60,
    "category": ["study"],
    "location": "Library",
    "importance": 0.8,
    "fixed_time": false,
    "fixed_start": null
  },
  "created_at": "2026-04-05T10:30:00"
}
```

### Source Context Values
| Value | Meaning |
|-------|---------|
| `main_schedule` | Task is in committed `main_schedule` |
| `unscheduled` | Task is in queue waiting for scheduling |
| `provisional` | Task is in working copy pending commit |

---
**Document prepared for ONIA 2026. All endpoints align with Database Schema v2.0, 5-stage pipeline, Draft Pattern, and synchronous MVP constraints.**
