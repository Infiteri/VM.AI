# VM.AI — Full Project Overview
**Competition:** ONIA 2026
**Status:** Architecture Complete, Full Pipeline Implemented

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

### Stage 4: Scheduler (Complete - v4.0)
- **Algorithm:** Stable Incremental Algorithm
- **Implementation:** ScheduleEngine class
- **Process:**
  1. Fetch tasks (hybrid: queue or task_ids list)
  2. Build free slot inventory
  3. Constraint solver
  4. **ALL slots scored** (not just top-15)
  5. Stable scoring with displacement handling
- **Scoring Formula:**
  ```
  score = base_value + free_boost - stability_penalty + location_boost + overlap_penalty + time_preference + urgency_boost
  ```
- **Key Parameters:**
  - TOP_N_CANDIDATES=400 (score all candidate slots)
  - FREE_SLOT_BOOST=0.5 (free slots bubble to top)
  - MAX_LAYER=1 (1-layer displacement max)
  - VALUE_THRESHOLD=0.25 (25% value threshold)
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

### 3.1 Class-Based Service Architecture
All core services follow a class-based pattern:
- **EnrichmentService** - Field enrichment, priority chain, importance recomputation
- **ScheduleEngine** - Scheduling with ALL slots scoring, displacement handling
- **TaskMatchingService** - Embedding-based task association
- **StatsRecorderService** - Two-denominator statistics updates
- **Hybrid schedule_batch** - Accepts optional task_ids or uses unscheduled queue

### 3.2 Draft System
- **Purpose:** Safe task creation via Chat/AI without polluting the main database
- **Flow:**
  1. User enters NLP prompt
  2. NLP Parser saves to `task_drafts`
  3. Frontend receives `draft_id` + clean `TaskPayload`
  4. User can edit fields before commit
  5. On commit: draft loaded → merged → saved to `tasks`
- **Safety:** If user abandons, background cleanup deletes drafts after 24 hours

### 3.3 Strict Validation
- All API schemas use Pydantic `Field` with constraints
- Automatic datetime ISO validation
- Model validators for `fixed_time` logic
- Catches 80% of errors at the boundary

### 3.4 Behavior-Aware Predictions
- Task-level statistics (from matched tasks)
- Category-level aggregates (fallback)
- Importance recalculation with deadline proximity
- Location preferences

### 3.5 Stable Scheduling
- Incremental updates (not full reschedule)
- 1-layer displacement maximum
- 25% value threshold
- **ALL slots scored** (not top-15) - ensures low-value tasks find free slots

### 3.6 Atomic Commits
- Single PostgreSQL transaction for schedule commit
- Prevents blank calendar on network drop

---

## 4. User Workflows

### 4.1 Manual Task Creation
```
1. User fills all fields in frontend form
2. Frontend calls POST /tasks with TaskPayload
3. Backend calls Task Matching
4. Backend computes urgency/value (EnrichmentService)
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

### 4.4 Schedule Batch (Hybrid Queue/Task IDs)
```
1. Frontend calls POST /schedule/batch (optional: task_ids list)
2. If task_ids provided: fetch specific tasks
3. If no task_ids: fetch from unscheduled_queue
4. ScheduleEngine.process_batch():
   a. Build free slot inventory
   b. For each task:
      - Get candidate slots (start_time window)
      - Score ALL slots (TOP_N_CANDIDATES=400)
      - Place in highest-scoring slot
      - Handle displacement if needed (MAX_LAYER=1)
5. Save to provisional_schedule
6. Record schedule_changes
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
| POST | `/schedule/batch` | `BatchScheduleRequest` (optional: task_ids) | `BatchScheduleResponse` |

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
| Enrichment | Complete (EnrichmentService class) |
| Scheduler | Complete (ScheduleEngine, ALL slots scored) |
| Stats Recorder | Complete (StatsRecorderService class) |

---

## 9. Key Implementation Details

### 9.1 ScheduleEngine Scoring
```
score = base_value + free_boost - stability_penalty + location_boost + overlap_penalty + time_preference + urgency_boost
```

Where:
- **base_value** = task.importance × urgency (normalized)
- **free_boost** = FREE_SLOT_BOOST (0.5) if slot is free
- **stability_penalty** = 0.15 × layer_displaced (1-layer max)
- **location_boost** = 0.3 × location_match (preferred location)
- **overlap_penalty** = -999 if overlaps (impossible)
- **time_preference** = 0.1 × time_match (preferred time blocks)
- **urgency_boost** = (1 - position_ratio) × 0.2 (near deadline)

### 9.2 Displacement Handling
- Only if displaced task importance × (1 - VALUE_THRESHOLD) >= new task importance
- MAX_LAYER=1 prevents cascade rescheduling
- Displaced tasks return to unscheduled_queue

### 9.3 Hybrid Batch Schedule
```python
def process_batch(self, db: Session, task_ids: list[str] | None = None) -> BatchScheduleResponse:
    if task_ids:
        tasks = self._fetch_specific_tasks(db, task_ids)
    else:
        tasks = self._fetch_queue_tasks(db)
```

---

*Document prepared for ONIA 2026.*