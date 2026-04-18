# VM.AI — Full Project Overview
**Competition:** ONIA 2026
**Status:** Architecture Complete, Core Pipeline Implemented

---

## 1. Core Value Proposition

VM.AI is an AI-driven personal scheduling system that transforms natural language input into optimized, behavior-aware calendar schedules. It prioritizes **schedule stability** and **predictable performance**.

The system learns from user's task completion patterns to make intelligent predictions about task duration, difficulty, and importance, while ensuring scheduled tasks don't thrash the user's calendar unexpectedly.

---

## 2. The 5-Stage Pipeline

### Stage 1: NLP Parser
- **Input:** Natural language text (e.g., "finish chemistry homework before Friday")
- **Process:** T5-base conditional generation → JSON parsing → Pydantic validation
- **Output:** `TaskPayload` with `{value, predicted}` structure for each field
- **Model:** Fine-tuned T5-base transformer
- **Workflow:** Saves to `task_drafts` table → Returns `draft_id` to frontend

### Stage 2: Task Matching
- **Input:** Parsed task name
- **Process:** 
  1. Exact case-insensitive match
  2. MiniLM embeddings + Cosine similarity
  3. Threshold classification
- **Thresholds:** 
  - ≥0.92 → `"same"` (identical task)
  - 0.65-0.91 → `"similar"` (related task)
  - <0.65 → `"none"` (new task)
- **Output:** `{associated_id, association_status, name_vector}`
- **Invariant:** `associated_id` points to `tasks_statistics.id`, never `tasks.id`

### Stage 3: Enrichment
- **Input:** Parsed task + Match result
- **Process:** 
  1. Date resolution (dateparser strict config)
  2. Historical averaging based on match status
  3. Importance recomputation with deadline boost
  4. Compute urgency and value
- **Priority Chain:**
  - Task statistics (only if `records >= 3`)
  - Category statistics (loop by priority)
  - Keep predicted value (cold start defaults to 0.5)
- **Output:** Full task data ready for DB insertion

### Stage 4: Scheduler
- **Algorithm:** Stable Incremental Algorithm
- **Process:**
  1. Fetch unscheduled tasks (FIFO order)
  2. Constraint solver
  3. Top-15 pruning
  4. Stable scoring
  5. 1-layer displacement max
- **Scoring Formula:**
  ```
  score = base_value + free_boost - stability_penalty + location_boost + overlap_penalty + time_preference
  ```
- **Guards:**
  - 12s hard timeout
  - Early termination if score < 0.35
  - 25% value threshold for displacement
- **Output:** Writes to `provisional_schedule` + `schedule_changes`

### Stage 5: Stats Recorder
- **Execution:** Synchronous in same DB transaction
- **Two Denominators:**
  - Plan averages → `records` (updated on commit)
  - Delta averages → `completed_count` (updated on rating)
- **Radial Decay:**
  ```
  boost = base × (1 - blocks × 0.25)
  ```
- **Weekly Normalization:** `×0.99` to prevent saturation

---

## 3. Key Features

### 3.1 Draft System
- **Purpose:** Safe task creation via Chat/AI without polluting the main database
- **Flow:**
  1. User enters NLP prompt
  2. NLP Parser saves to `task_drafts`
  3. Frontend receives `draft_id` + clean `TaskPayload`
  4. User can edit fields before commit
  5. On commit: draft loaded → merged → saved to `tasks`
- **Safety:** If user abandons, background cleanup deletes drafts after 24 hours

### 3.2 Strict Validation
- All API schemas use Pydantic `Field` with constraints
- Automatic datetime ISO validation
- Model validators for `fixed_time` logic
- Catches 80% of errors at the boundary

### 3.3 Behavior-Aware Predictions
- Task-level statistics (from matched tasks)
- Category-level aggregates (fallback)
- Importance recalculation with deadline proximity
- Location preferences

### 3.4 Stable Scheduling
- Incremental updates (not full reschedule)
- 1-layer displacement maximum
- 25% value threshold
- 12s timeout

### 3.5 Atomic Commits
- Single PostgreSQL transaction for schedule commit
- Prevents blank calendar on network drop

---

## 4. User Workflows

### 4.1 Manual Task Creation
```
1. User fills all fields in frontend form
2. Frontend calls POST /tasks with TaskPayload
3. Backend calls Task Matching
4. Backend computes urgency/value
5. Backend creates task + statistics + categories
6. Backend adds to unscheduled queue
7. Return task_id + status
```

### 4.2 NLP Task Creation (Add Mode)
```
1. User enters NLP prompt
2. Frontend calls POST /tasks/parse/add
3. Backend runs NLP Parser → TaskPayload
4. Backend saves to task_drafts → returns draft_id
5. Frontend shows preview + edit options
6. User edits (optional)
7. Frontend calls POST /tasks with draft_id
8. Backend loads draft → merges with edits
9. Continue as Manual Creation
```

### 4.3 NLP Task Modification
```
1. User selects task to modify
2. Frontend calls GET /tasks/{id}
3. User enters modification prompt
4. Frontend calls POST /tasks/parse/modify (task: TaskPayload, prompt)
5. Backend runs NLP Parser on changes
6. Backend merges changes with existing
7. Frontend shows modified task
```

---

## 5. API Endpoints Summary

### Tasks
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/tasks` | `TaskCreateRequest` | `TaskResponse` |
| GET | `/tasks/{id}` | - | `TaskDetailResponse` |
| DELETE | `/tasks/{id}` | - | `SuccessResponse` |
| POST | `/tasks/parse/add` | `ParseAddRequest` | `ParseAddResponse` |
| POST | `/tasks/parse/modify` | `ParseModifyRequest` | `ParseModifyResponse` |

### Schedule
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/schedule` | - | `ScheduleResponse` |
| POST | `/schedule/batch` | - | `BatchScheduleResponse` |

### Provisional
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/provisional/changes` | - | `ProvisionalChangesResponse` |
| POST | `/provisional/commit` | - | `SuccessResponse` |
| POST | `/provisional/reset` | - | `SuccessResponse` |

### Stats
| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/tasks/{id}/rate` | `RateRequest` | `RateResponse` |

---

## 6. Error Handling

| Status Code | Meaning | Cause |
|------------|---------|-------|
| 422 | Validation Error | Pydantic rejects malformed input |
| 404 | Not Found | Invalid UUID or missing task |
| 409 | Conflict | Task already rated, duplicate scheduled |
| 500 | Server Error | Catch-all, log boundary, return safe message |

---

## 7. Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15+ |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| NLP Model | T5-base (fine-tuned) |
| Embeddings | MiniLM |
| Date Parsing | dateparser |

---

## 8. Development Status

| Component | Status |
|-----------|--------|
| API Schemas | Complete |
| Database Models | Complete |
| Task Matching | Complete |
| NLP Parser | Complete |
| Enrichment | Complete |
| Scheduler | Not Started |
| Stats Recorder | Not Started |

---

*Document prepared for ONIA 2026.*