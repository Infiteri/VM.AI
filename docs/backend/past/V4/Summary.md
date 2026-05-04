# VM.AI Backend — Technical Summary
**Version:** 3.0 (Final)
**Last Updated:** April 18, 2026
**Competition:** ONIA 2026

---

## 1. System Overview

VM.AI is an AI-driven personal scheduling system that transforms natural language input into optimized, behavior-aware calendar schedules. The system prioritizes **schedule stability** and **predictable performance** through a 5-stage pipeline.

### 1.1 Core Value Proposition
- **Natural Language Input:** Users describe tasks in plain language
- **Behavior-Aware:** System learns from user's task completion patterns
- **Stable Schedules:** Prevents schedule thrashing through incremental updates
- **Draft Safety:** Safe task creation via Chat without polluting the main database

---

## 2. The 5-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              5-Stage Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Stage 1: NLP Parser                                                       │
│   Input: "finish chemistry homework before Friday"                         │
│   Process: T5-base conditional generation → JSON parsing                    │
│   Output: TaskPayload (clean fields, {value, predicted} structure)          │
│   Dependencies: transformers, sentence-transformers                         │
│                                                                             │
│   Stage 2: Task Matching                                                   │
│   Input: Task name                                                         │
│   Process: Exact match → MiniLM embeddings → Cosine similarity              │
│   Thresholds: ≥0.92 = "same", 0.65-0.91 = "similar", <0.65 = "none"      │
│   Output: {associated_id, association_status, name_vector}                  │
│   Dependencies: sentence-transformers                                       │
│                                                                             │
│   Stage 3: Enrichment                                                     │
│   Input: TaskPayload + Match result                                          │
│   Process: Date resolution → Historical averaging → Compute urgency/value        │
│   Priority: task_statistics (records≥3) → category_statistics → keep value   │
│   Output: Full task data ready for DB insertion                           │
│   Dependencies: dateparser, SQLAlchemy                                   │
│                                                                             │
│   Stage 4: Scheduler                                                      │
│   Input: Task list from unscheduled_queue                                    │
│   Process: Constraint solver → Top-15 pruning → Stable scoring            │
│   Constraints: 12s timeout, 1-layer displacement, 25% value threshold    │
│   Output: provisional_schedule + schedule_changes                        │
│   Dependencies: None (pure algorithm)                                    │
│                                                                             │
��   Stage 5: Stats Recorder                                                 │
│   Input: Completed/rated task + actual values                           │
│   Process: Synchronous update with two denominators                      │
│   Denominators: records (plan), completed_count (delta)                   │
│   Output: Updated statistics tables                                      │
│   Dependencies: SQLAlchemy                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Architectural Decisions

### 3.1 Draft System Pattern
- **Purpose:** Safe task creation via Chat without polluting the main database
- **Flow:**
  1. User enters NLP prompt → NLP Parser processes → saves to `task_drafts`
  2. Frontend receives `draft_id` + clean `TaskPayload`
  3. User can edit fields before commit
  4. On commit: draft is loaded (match_result from content) → merged → saved to `tasks`
- **Safety:** If user abandons, background cleanup deletes drafts after 24 hours

### 3.2 No Predicted Flags in API
- Frontend receives clean `TaskPayload` with no internal flags
- Backend handles all overwrite logic internally by comparing:
  - Draft data (from NLP) vs User edits (source of truth)
  - `predicted: true` fields → checked against statistics
  - `predicted: false` fields → kept as user provided

### 3.3 Strict Validation
- All schemas use Pydantic `Field` with constraints:
  - `difficulty`: 0.0 - 1.0
  - `duration`: 1 - 1439 minutes
  - `importance`: 0.0 - 1.0
- All temporal fields are `datetime` types (automatic ISO validation)
- Model validators enforce `fixed_time` logic

### 3.4 Atomic Operations
- Schedule commit uses single PostgreSQL transaction:
  ```sql
  BEGIN
  DELETE FROM main_schedule
  INSERT INTO main_schedule SELECT * FROM provisional_schedule
  TRUNCATE schedule_changes
  COMMIT
  ```
- Prevents blank calendar on network drop

### 3.5 Background Cleanup
- Async task runs every 24 hours
- Deletes old drafts: `DELETE FROM task_drafts WHERE created_at < NOW() - INTERVAL '24 hours'`

---

## 4. Database Schema (v3.0)

### 4.1 Table Groups

| Group | Tables | Purpose |
|-------|--------|---------|
| **Core** | `tasks`, `main_schedule`, `provisional_schedule`, `schedule_changes` | Task definitions & calendar slots |
| **Workflow** | `unscheduled_tasks`, `task_drafts` | FIFO queue, temporary draft storage |
| **Statistics** | `tasks_statistics`, `category_statistics` | Behavioral learning data |
| **Normalization** | `categories`, `locations`, `task_categories`, `*_statistics_locations` | Master lists & junctions |

### 4.2 Key Constraints
- **Single-user system** — no `user_id` fields anywhere
- **No status field** — task state derived from table presence
- **Statistics persistence** — NEVER cascade-deleted when task is deleted
- **10-day rolling window** — scheduled tasks kept for 10 days

---

## 5. API Endpoints (v3.0)

### 5.1 Tasks Endpoints
| Method | Endpoint | Purpose |
|--------|---------|---------|
| POST | `/tasks` | Create task (manual or from draft) |
| GET | `/tasks/{id}` | Get task details |
| DELETE | `/tasks/{id}` | Delete task |
| POST | `/tasks/parse/add` | Parse NLP to draft |
| POST | `/tasks/parse/modify` | Parse modification prompt |

### 5.2 Schedule Endpoints
| Method | Endpoint | Purpose |
|--------|---------|---------|
| GET | `/schedule` | Get main schedule |
| POST | `/schedule/batch` | Run scheduler |

### 5.3 Provisional Endpoints
| Method | Endpoint | Purpose |
|--------|---------|---------|
| GET | `/provisional/changes` | Get pending changes |
| POST | `/provisional/commit` | Commit changes |
| POST | `/provisional/reset` | Reset provisional |

### 5.4 Stats Endpoints
| Method | Endpoint | Purpose |
|--------|---------|---------|
| POST | `/tasks/{id}/rate` | Rate task completion |

---

## 6. Data Flow Examples

### 6.1 Manual Task Creation
```
Frontend → POST /tasks (TaskPayload)
         → Task Matching (MiniLM)
         → Enrichment (compute urgency/value)
         → DB: create task, category associations
         → DB: add to unscheduled_queue
         → Response: task_id, status
```

### 6.2 NLP Task Creation
```
Frontend → POST /tasks/parse/add (prompt)
         → NLP Parser (T5)
         → DB: save to task_drafts
         → Response: draft_id, TaskPayload
         
Frontend → Edit fields (optional)
         → POST /tasks (draft_id)
         → Load draft + merge with edits
         → Continue as Manual Creation
```

### 6.3 NLP Task Modification
```
Frontend → GET /tasks/{id} (get current task)
         → POST /tasks/parse/modify (task: TaskPayload, prompt)
         → NLP Parser (extract changes)
         → Merge with existing
         → Response: modified TaskPayload
```

---

## 7. Field Overwrite Logic (Enrichment)

### 7.1 Overwrite Priority
For each field with `predicted: true`:
1. Check `task_statistics` (if `records >= 3`)
2. Loop through `category_statistics` (by priority)
3. If nothing found → keep predicted value

### 7.2 Duration Bucket Logic
Buckets are: `0.0`, `0.5`, `1.0`
- If `difficulty` is predicted → use statistics difficulty for bucket lookup
- If `difficulty` is explicit → use actual difficulty for bucket lookup

### 7.3 Importance Recomputation
```
base = nlp_importance
deadline_boost = 0.3 (days_left ≤ 1)
               = 0.2 (days_left ≤ 3)
               = 0.1 (days_left ≤ 7)
               = 0 otherwise
completion_boost = completion_rate × 0.2
final = min(1.0, base + deadline_boost + completion_boost)
```

---

## 8. Statistics Structure

### 8.1 avg_duration Structure (v3.0)
```python
# Both TaskStatistics and CategoryStatistics
{
    "0.0": {"count": 5, "avg": 30},
    "0.5": {"count": 3, "avg": 45},
    "1.0": {"count": 4, "avg": 45}
}
```

### 8.2 Two Denominators
| Average Type | Denominator | When Updated |
|-------------|------------|--------------|
| Plan averages (`avg_duration`, `avg_difficulty`) | `records` | On task commit |
| Delta averages (`avg_duration_delta`, `avg_difficulty_delta`) | `completed_count` | On task rating |

---

## 9. Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI Backend | 100% | Full application running |
| Database Models | 100% | All v3.0 tables |
| Pydantic Schemas | 100% | Strict validation |
| Task Matching | 100% | MiniLM + thresholds |
| NLP Parser | 100% | Trained T5 model |
| Enrichment | 100% | All methods implemented |
| Scheduler | 0% | Not implemented |
| Stats Recorder | 0% | Not implemented |

---

## 10. Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15+ |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| NLP | T5-base |
| Embeddings | MiniLM |
| Date Parsing | dateparser |

---

## 11. File Structure

```
src/backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── core/                 # Config, database, logging
│   ├── api/v1/endpoints/    # Route handlers
│   ├── models/              # SQLAlchemy ORM
│   ├── schemas/            # Pydantic models
│   ├── services/          # Business logic
│   └── utils/             # Utilities
├── alembic/               # Database migrations
��── logs/                  # Application logs
└── pyproject.toml         # Dependencies
```

---

*Document prepared for ONIA 2026. This summary reflects the current v3.0 implementation state as of April 18, 2026.*