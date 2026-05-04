```markdown
# VM.AI — Full Project Overview
**Competition:** ONIA 2026 (National AI Olympiad of Moldova)  
**Timeline:** 1 Month to Implementation  
**Architecture:** Competition-Ready, Stable Incremental Pipeline  
**Last Updated:** April 6, 2026  
**Database:** PostgreSQL 15+  
**API Version:** 2.2 (Final)

---

## 🎯 Executive Summary

VM.AI is an AI-driven personal scheduling system that transforms natural language input into optimized, behavior-aware calendar schedules. The system learns continuously from user completions, corrections, and time preferences, improving prediction accuracy and scheduling relevance over time. Built for a single-user competition context, it prioritizes **schedule stability**, **predictable performance**, and **mathematical soundness** over global algorithmic perfection.

### Core Value Proposition
- **Natural Language First:** Users describe tasks conversationally; the system handles the complexity.
- **Stable Incremental Scheduling:** Tasks don't jump around unnecessarily; changes are intentional and value-driven.
- **Behavioral Learning:** The system adapts to your actual duration estimates, difficulty perceptions, and preferred time slots.
- **Transparent Enrichment:** Every field carries a `predicted` flag so users know what was stated vs. estimated.
- **Competition-Ready:** CPU-only inference, synchronous MVP execution, atomic transactions, and graceful degradation.

---

## 🏗️ Core Architecture: 5-Stage Pipeline

All processing follows a strict, unidirectional pipeline with clearly defined input/output contracts:

```text
User Input (Add/Modify via Chat or Form)
   ↓
[1] NLP Parser → structured JSON + predicted flags
   ↓
[2] Task Matching → {name_vector, associated_id, association_status}
   ↓
[3] Enrichment → resolves dates, applies historical averages, writes to DB
   ↓
[4] Scheduling Engine → stable incremental placement (7-day horizon)
   ↓
[5] Stats Recorder → synchronous MVP updates of behavioral metrics
```

### Pipeline Guarantees
- **Deterministic:** Same input → same output (no stochastic sampling)
- **Bounded Complexity:** `O(N × 15)` scheduling, `<12s` hard timeout
- **Atomic Operations:** All state changes wrapped in PostgreSQL transactions
- **Graceful Degradation:** ML failures fallback to regex + defaults; never `500` to user

---

## 📦 Module Breakdown

### 1. NLP Parser (v3.0)
| Property | Value |
|----------|-------|
| **Model** | Fine-tuned `T5-base` (220M params, ~900MB) |
| **Operations** | `Add` (full extraction), `Modify` (delta extraction), `Delete` (backend-only) |
| **Key Output** | Every field: `{ "value": <type>, "predicted": bool }` |
| **Date Handling** | Raw strings passed through (`"Friday"`, `"next Monday"`). Resolved by Enrichment. |
| **Validation** | JSON parse + Pydantic schema enforcement before pipeline handoff |
| **Fallback** | Lightweight regex extractor if ML service fails |

**Predicted Flag Semantics:**
- `predicted: false` → User stated explicitly. Backend will **never** override.
- `predicted: true` → Model estimated. Backend **may** replace with historical data during enrichment.

---

### 2. Task Matching Model (v2.4)
| Property | Value |
|----------|-------|
| **Model** | `paraphrase-MiniLM-L6-v2` (384-dim vectors, off-the-shelf) |
| **Process** | Exact case-insensitive string match → Cosine similarity fallback |
| **Thresholds** | `≥0.92` → `"same"`, `0.65–0.91` → `"similar"`, `<0.65` → `"none"` |
| **Output** | `{ name_vector, associated_id, association_status }` |
| **Critical Detail** | `associated_id` points to `tasks_statistics.id`, **never** `tasks.id` |

**Matching Flow:**
1. Exact string pre-filter (fast path, ~30% of inputs)
2. Cosine similarity against all `task_name_vector` in `tasks_statistics`
3. Classification via fixed thresholds
4. Return lightweight payload to Enrichment

---

### 3. Enrichment Module (v4.0)
| Property | Value |
|----------|-------|
| **Purpose** | Replace NLP estimates (`predicted: true`) with historical data when reliable |
| **Data Priority** | Matched task (`records ≥ 3`) → Category stats → Cold start defaults |
| **Core Formulas** | `duration = avg_duration + avg_duration_delta`<br>`difficulty = avg_difficulty + avg_difficulty_delta`<br>`urgency = min(1.0, importance × (1/days_left) × 3)`<br>`value = (imp×0.4 + urg×0.4 + diff×0.2) × completion_rate` |
| **Date Parsing** | Strict `dateparser` config: `PREFER_DATES_FROM: future`, `RELATIVE_BASE: now` |
| **DB Writes** | Creates/locates `tasks_statistics`, inserts `tasks` row, adds to `unscheduled_tasks` |

**Enrichment Decision Tree:**
```text
If association_status = "same" AND records >= 3:
    Use matched task's statistics row
Elif association_status = "similar" AND matched records >= 3:
    Use matched task's statistics row for deltas, category for base
Else:
    Use category_statistics only
```

---

### 4. Scheduling Engine (v4.0 — Stable Incremental)
| Property | Value |
|----------|-------|
| **Horizon** | 7-day rolling window, 15-min granularity (672 slots) |
| **Algorithm** | Constraint Solver → Top-15 Pruning → Stable Scoring → 1-Layer Displacement |
| **Scoring Formula** | `slot_score = base_score + free_slot_boost - stability_penalty + location_continuity + overlap_penalty + time_preference_boost` |
| **Stability Rules** | • `-0.50` penalty if slot occupied<br>• `+0.15` boost if slot free<br>• Displace only if `new.value ≥ existing.value × 1.25`<br>• Moved tasks become `fixed=True` for remainder of run<br>• Max 1 displacement layer per batch |
| **Execution Guards** | • Hard 12s timeout<br>• Early termination if `best_score < 0.35`<br>• FIFO ordering from `unscheduled_tasks` |
| **Output** | Writes to `provisional_schedule` + `schedule_changes`, removes from `unscheduled_tasks` |

**Why Stable Incremental Over CP-SAT:**
- ✅ Preserves UX trust (tasks don't jump unnecessarily)
- ✅ Bounded `O(N × 15)` complexity vs. exponential search
- ✅ Zero DB schema changes required
- ✅ Easy to implement (~10 lines added to existing Slot Ranker)

---

### 5. Stats Recorder (v2.0 — Synchronous MVP)
| Property | Value |
|----------|-------|
| **Execution** | Runs in same DB transaction as triggering action (prevents race conditions) |
| **Two Denominator System** | • **Plan Averages** (`avg_duration`, `avg_difficulty`): Denominator = `records` (updated on every commit)<br>• **Delta Averages** (`avg_duration_delta`, `avg_difficulty_delta`): Denominator = `completed_count` (updated only on completion) |
| **Time Preference Scoring** | Radial decay `0.25/15min`, max `10.0`. Updated on: Schedule (`+1.0`), Commit (`+2.0`), Move (`-2.0` original / `+1.0` new) |
| **Never Updates** | `associated_task_statistics_id` (read-only for enrichment) |
| **Weekly Decay** | `×0.99` normalization via cron to prevent score saturation |

**Atomic JSONB Update Pattern:**
```python
# Python computes radial boosts
update_dict = {"10:00": 2.5, "10:15": 1.75}
# PostgreSQL applies atomically
UPDATE tasks_statistics 
SET task_time_scores = task_time_scores || %s 
WHERE id = %s;
```

---

## 🔄 User Workflow & State Management

| Step | Action | System State Change |
|------|--------|-------------------|
| 1 | Add/Modify Task | NLP → Match → Enrich → `tasks` + `unscheduled_tasks` + `tasks_statistics` |
| 2 | Schedule Tasks | FIFO processing → `provisional_schedule` + `schedule_changes` |
| 3 | Review/Modify | Pull back to `unscheduled_tasks` if adjusted |
| 4 | Commit | Atomic copy: `provisional_schedule → scheduled_slots`. Clears `schedule_changes`. |
| 5 | Complete & Rate | Synchronous stats update → plan/delta averages + time scores. Sets `tasks.rated = TRUE`. |
| 6 | Delete | Hard cascade from `tasks` (based on `source` context). Statistics row preserved. |

### State Derivation (No `status` Field)
Task state is inferred from table presence:
- In `unscheduled_tasks` → waiting for scheduling
- In `provisional_schedule` → staged for commit
- In `scheduled_slots` → committed/main schedule

### Source Context Parameter
All delete/modify operations require a `source` query parameter to determine cascade behavior:

| Source Value | Tables Affected on Delete | Tables Affected on Modify |
|--------------|---------------------------|---------------------------|
| `main_schedule` | `scheduled_slots` + `tasks` | Pull from `scheduled_slots` → create new in `unscheduled_tasks` |
| `unscheduled` | `unscheduled_tasks` only | Update `unscheduled_tasks` entry |
| `provisional` | `provisional_schedule` + `schedule_changes` | Pull from `provisional` → create new in `unscheduled_tasks` |

---

## 🗄️ Database Architecture

### Table Groups
| Group | Tables | Purpose |
|-------|--------|---------|
| **Core** | `tasks`, `scheduled_slots`, `provisional_schedule`, `schedule_changes` | Task definitions, committed schedule, working copy, change log |
| **Workflow** | `unscheduled_tasks` | FIFO queue of tasks awaiting placement |
| **Statistics** | `tasks_statistics`, `category_statistics` | Behavioral averages, deltas, location counts, time preference scores |

### Key Schema Additions (v1.9)
```sql
-- Rated flag for UI state tracking
ALTER TABLE tasks ADD COLUMN rated BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX idx_tasks_rated ON tasks (rated);

-- Performance indexes
CREATE INDEX idx_provisional_range ON provisional_schedule (start, end);
CREATE INDEX idx_scheduled_range ON scheduled_slots (start, end);
CREATE INDEX idx_unscheduled_fifo ON unscheduled_tasks (created_at);
```

### Critical Relationships
- **Two-link design:** `tasks.task_statistics_id` (own stats) + `tasks.associated_task_statistics_id` (matched stats)
- **Shared Row Invariant:** When `association_status = "same"`, both FKs point to the same `tasks_statistics` row
- **Cascade Rules:** Core tables cascade to each other (`ON DELETE CASCADE`). Statistics tables use `ON DELETE NO ACTION` to preserve historical data.
- **10-Day Rolling Window:** Tasks outside 3 past + 1 current + 6 future days become immutable/archived.

---

## 📡 API Contract Summary (v2.2 — Final)

**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** None (single-user MVP)

### 12 Core Endpoints

| Endpoint | Method | Purpose | Key Parameters |
|----------|--------|---------|---------------|
| `/schedule` | GET | Fetch committed tasks for a date | `date=YYYY-MM-DD` |
| `/tasks/{id}/rate` | POST | Record completion + ratings | `completed`, `actual_duration?`, `actual_difficulty?` |
| `/tasks/{id}` | DELETE | Delete task (context-aware) | `source=main_schedule\|unscheduled\|provisional` |
| `/tasks/parse/modify` | POST | NLP parse for modification | `task_id`, `prompt` |
| `/tasks/{id}/update` | POST | Submit modified task | `source`, `task` object with `predicted` flags |
| `/tasks/parse/add` | POST | NLP parse for new task | `prompt` |
| `/tasks` | POST | Create new task | `task` object with `predicted` flags |
| `/unscheduled` | GET | Fetch unscheduled queue | `limit` |
| `/schedule/batch` | POST | Trigger stable scheduler | `{}` (empty body) |
| `/provisional/changes` | GET | Fetch pending schedule changes | None |
| `/provisional/reset` | POST | Discard provisional changes | `{}` |
| `/provisional/commit` | POST | Atomically commit provisional → main | `{}` |

### Request/Response Conventions
- **Task Objects:** All fields use `{ "value": <type>, "predicted": bool }` structure in POST requests
- **Success Responses:** Always include `"success": true` field
- **Error Responses:** Consistent `{ "detail", "error_code", "timestamp" }` structure
- **Confirmation Handling:** All confirmations are GUI-side; backend endpoints execute immediately

---

## 🔑 Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Stable Incremental Scheduler** | Preserves UX trust. Prevents schedule thrashing. Bounded `O(N×15)` complexity. |
| **Synchronous Stats (MVP)** | Eliminates race conditions on averages. ~50ms overhead acceptable for competition scope. |
| **Predicted Flags** | Clean separation of user intent vs model estimation. Drives deterministic enrichment rules. |
| **Additive Time Preference** | Max `10.0` ensures user preference dominates generic scoring without multiplicative instability. |
| **No Status Field** | Reduces schema complexity. State is derived from relational presence (cleaner workflow). |
| **10-Day Data Window** | Simplifies overlap checks, stats processing, and UI. Prevents unbounded DB growth. |
| **PostgreSQL Native Types** | Leverages `UUID`, `JSONB`, `TEXT[]`, `FOR UPDATE SKIP LOCKED` for clean, efficient implementation. |
| **Unified `source` Parameter** | Single delete/modify endpoint with context-aware cascade logic reduces API surface and frontend complexity. |

---

## 🚫 Scope & Constraints

### ✅ In Scope (Competition Delivery)
- Natural language task creation & modification with `predicted` flags
- Semantic task matching & historical enrichment
- Stable incremental scheduling with displacement safeguards
- Provisional workflow & atomic commit
- Synchronous behavioral stats & time preference learning
- Single-user, CPU-only inference, 7-day horizon
- **12 finalized API endpoints** with `source` context and `rated` flag support

### ❌ Out of Scope (Documented for Future)
- Recurring task templates & cron instance generation
- Multi-user authentication & role management
- Enrichment log storage (written to app logs only)
- Complex multi-layer displacement (>1 layer)
- CP-SAT global optimization (rejected for UX stability)
- Async Stats Recorder (synchronous for MVP)

---

## 📈 Implementation Status & Next Steps

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Foundation | 🟢 Complete | DB schema v1.9, indexes, Pydantic validators, dateparser config |
| API Contracts | 🟢 Complete | 12 endpoints defined, `source` logic unified, `rated` flag added |
| Core Pipeline | 🟡 In Progress | NLP → Match → Enrich → Stable Scheduler → Sync Stats |
| Workflow | 🟡 In Progress | Provisional scheduling, change logging, atomic commit |
| Demo Prep | ⚪ Pending | Synthetic seeding, fallback paths, video backup |

### Critical Path (Next 2 Weeks)
1. Implement stable scheduler scoring + atomic commit transaction
2. Wire synchronous Stats Recorder with two-denominator math
3. Validate enrichment deltas + radial time preference updates
4. Generate FastAPI route stubs matching v2.2 contracts
5. Freeze code 48h before demo; only fix critical bugs

---

## 💡 Final Architecture Notes

### Reliability > Perfection
A stable, predictable 80% system outperforms a brittle 100% optimizer in competition judging. Every module is designed to degrade gracefully under load or ML failure.

### Mathematical Soundness
The plan vs. delta separation in Stats Recorder ensures enrichment converges to real user behavior without drift. Two denominators (`records` vs `completed_count`) maintain statistical validity.

### Zero Black Boxes
Every module is deterministic, auditable, and logs boundaries (`NLP_DONE`, `ENRICHED`, `SCHEDULED`, `STATS_UPDATED`). Debugging during live demos is possible.

### Demo-Ready by Design
- 10-day window simplifies overlap checks and UI
- Synchronous stats eliminate race conditions
- Atomic commits guarantee consistent state
- Stability penalties prevent schedule thrashing
- Fallback regex parser ensures system never shows `500` to judges

### Competition Execution Checklist
- [ ] All 12 endpoints implemented and tested
- [ ] PostgreSQL indexes created for performance
- [ ] Synthetic stats pre-seeded for warm demo
- [ ] Backup demo video recorded
- [ ] 1-page failure runbook written
- [ ] Code frozen 48h before presentation

---

**Document prepared for ONIA 2026.**  
All specifications align with Database Schema v1.9, API Contracts v2.2, and the 1-month implementation timeline.  
*Next Step: Generate production-ready FastAPI route stubs or begin SQLAlchemy model implementation.*
```