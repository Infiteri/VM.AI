# VM.AI — Full Project Overview
**Competition:** ONIA 2026 (National AI Olympiad of Moldova)  
**Timeline:** 1 Month to Implementation  
**Architecture:** Competition-Ready, Stable Incremental Pipeline  
**Last Updated:** April 5, 2026

---

## 🎯 Executive Summary
VM.AI is an AI-driven personal scheduling system that transforms natural language input into optimized, behavior-aware calendar schedules. The system learns continuously from user completions, corrections, and time preferences, improving prediction accuracy and scheduling relevance over time. Built for a single-user competition context, it prioritizes **schedule stability**, **predictable performance**, and **mathematical soundness** over global algorithmic perfection.

---

## 🏗️ Core Architecture: 5-Stage Pipeline
All processing follows a strict, unidirectional pipeline with clearly defined input/output contracts:

```
User Input (Add/Modify)
   ↓
[1] NLP Parser → structured JSON + predicted flags
   ↓
[2] Task Matching → {name_vector, associated_id, association_status}
   ↓
[3] Enrichment → applies historical averages, deltas, urgency/value
   ↓
[4] Scheduling Engine → stable incremental placement (7-day horizon)
   ↓
[5] Stats Recorder → synchronous MVP updates of behavioral metrics
```

---

## 📦 Module Breakdown

### 1. NLP Parser (v3.0)
- **Model:** Fine-tuned `T5-base` (220M params, ~900MB, CPU-friendly)
- **Operations:** 
  - `Add`: Extracts all fields from conversational prompts
  - `Modify`: Outputs only delta fields given existing task JSON + change prompt
  - `Delete`: Handled directly by backend (no NLP)
- **Key Output:** Every field carries `predicted: false` (explicit) or `predicted: true` (estimated)
- **Date Handling:** Raw strings (`"Friday"`, `"next Monday 3pm"`) passed through. Parsed downstream.
- **Validation:** JSON parse + Pydantic schema enforcement before pipeline handoff.

### 2. Task Matching Model (v2.4)
- **Model:** `paraphrase-MiniLM-L6-v2` (384-dim vectors, off-the-shelf)
- **Process:** Exact case-insensitive string match → Cosine similarity fallback
- **Thresholds:** `≥0.92` → `"same"`, `0.65–0.91` → `"similar"`, `<0.65` → `"none"`
- **Output:** `{name_vector, associated_id, association_status}`
- **Critical Detail:** `associated_id` points to `tasks_statistics.id`, not `tasks.id`.

### 3. Enrichment Module (v4.0)
- **Purpose:** Replaces NLP estimates (`predicted: true`) with historical data when reliable.
- **Data Priority:** Matched task (`records ≥ 3`) → Category stats → Cold start defaults
- **Core Formulas:**
  - `duration = avg_duration + avg_duration_delta`
  - `difficulty = avg_difficulty + avg_difficulty_delta`
  - `urgency = min(1.0, importance × (1/days_left) × 3)`
  - `value = (imp×0.4 + urg×0.4 + diff×0.2) × completion_rate`
- **Date Parsing:** Strict `dateparser` config (`PREFER_DATES_FROM: future`, `RELATIVE_BASE: now`)
- **DB Writes:** Creates/locates `tasks_statistics`, inserts `tasks` row, adds to `unscheduled_tasks`.

### 4. Scheduling Engine (v4.0 — Stable Incremental)
- **Horizon:** 7-day rolling window, 15-min granularity
- **Algorithm:** Constraint Solver → Top-15 Candidate Pruning → Slot Ranker → 1-Layer Displacement
- **Scoring Formula:**
  ```
  slot_score = base_score 
             + free_slot_boost(+0.15 if free) 
             - stability_penalty(0.50 if occupied) 
             + location_continuity_boost 
             + overlap_penalty 
             + time_preference_boost(additive, max 10.0)
  ```
- **Stability Rules:** 
  - Max 1 displacement layer per batch run
  - Displacement requires `new.value ≥ existing.value × 1.25`
  - Moved tasks become `fixed=True` for the remainder of the run
  - Hard 12s timeout, early termination if `best_score < 0.35`
- **Output:** Writes to `provisional_schedule` & `schedule_changes`, removes from `unscheduled_tasks`.

### 5. Stats Recorder (v2.0 — Synchronous MVP)
- **Execution:** Runs in the same DB transaction as the triggering action (prevents race conditions)
- **Two Denominator System:**
  - **Plan Averages** (`avg_duration`, `avg_difficulty`): Denominator = `records` (updated on every commit)
  - **Delta Averages** (`avg_duration_delta`, `avg_difficulty_delta`): Denominator = `completed_count` (updated only on completion)
- **Time Preference Scoring:** Radial decay `0.25/15min`, max `10.0`. Updated on Schedule (`+1.0`), Commit (`+2.0`), Move (`-2.0` original / `+1.0` new)
- **Never Updates:** `associated_task_statistics_id` (read-only for enrichment)

---

## 🔄 User Workflow & State Management

| Step | Action | System State Change |
|------|--------|---------------------|
| 1 | **Add/Modify Task** | NLP → Match → Enrich → `tasks` + `unscheduled_tasks` + `tasks_statistics` |
| 2 | **Schedule Tasks** | FIFO processing → `provisional_schedule` + `schedule_changes` |
| 3 | **Review/Modify** | Pull back to `unscheduled_tasks` if adjusted |
| 4 | **Commit** | Atomic copy: `provisional_schedule → scheduled_slots`. Clears `schedule_changes`. |
| 5 | **Complete & Rate** | Synchronous stats update → plan/delta averages + time scores |
| 6 | **Delete** | Hard cascade from `tasks`. Statistics row preserved for historical matching. |

**State Derivation:** No `status` field on tasks. State is inferred from table presence:
- In `unscheduled_tasks` → waiting for scheduling
- In `provisional_schedule` → staged for commit
- In `scheduled_slots` → committed/main schedule

---

## 🗄️ Database Architecture

| Group | Tables | Purpose |
|-------|--------|---------|
| **Core** | `tasks`, `scheduled_slots`, `provisional_schedule`, `schedule_changes` | Task definitions, committed schedule, working copy, change log |
| **Workflow** | `unscheduled_tasks` | FIFO queue of tasks awaiting placement |
| **Statistics** | `tasks_statistics`, `category_statistics` | Behavioral averages, deltas, location counts, time preference scores |

**Key Relationships:**
- Two-link design: `tasks.task_statistics_id` (own stats) + `tasks.associated_task_statistics_id` (matched stats)
- `association_status = "same"` → both FKs point to the same `tasks_statistics` row
- `ON DELETE NO ACTION` on statistics tables → stats persist for historical matching
- 10-day rolling window constraint: tasks outside 3 past + 1 current + 6 future days become immutable/archived

---

## 🔑 Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Stable Incremental Scheduler** | Preserves UX trust. Prevents schedule thrashing. Bounded `O(N×15)` complexity. |
| **Synchronous Stats (MVP)** | Eliminates race conditions on averages. ~50ms overhead is acceptable for competition scope. |
| **Predicted Flags** | Clean separation of user intent vs model estimation. Drives deterministic enrichment rules. |
| **Additive Time Preference** | Max `10.0` ensures user preference dominates generic scoring without multiplicative instability. |
| **No Status Field** | Reduces schema complexity. State is derived from relational presence (cleaner workflow). |
| **10-Day Data Window** | Simplifies overlap checks, stats processing, and UI. Prevents unbounded DB growth. |

---

## 🚫 Scope & Constraints

### ✅ In Scope (Competition Delivery)
- Natural language task creation & modification
- Semantic task matching & historical enrichment
- Stable incremental scheduling with displacement safeguards
- Provisional workflow & atomic commit
- Synchronous behavioral stats & time preference learning
- Single-user, CPU-only inference, 7-day horizon

### ❌ Out of Scope (Documented for Future)
- Recurring task templates & cron instance generation
- Multi-user authentication & role management
- Enrichment log storage (written to app logs only)
- Complex multi-layer displacement (>1 layer)
- CP-SAT global optimization (rejected for UX stability)

---

## 📈 Implementation Status & Next Steps

| Phase | Status | Deliverable |
|-------|--------|-------------|
| **Foundation** | 🔵 Ready | DB schema, indexes, Pydantic validators, `dateparser` config |
| **Core Pipeline** | 🟡 In Progress | NLP → Match → Enrich → Stable Scheduler → Sync Stats |
| **Workflow** | 🟡 In Progress | Provisional scheduling, change logging, atomic commit |
| **Demo Prep** | ⚪ Pending | Synthetic seeding, API contracts, fallback paths, video backup |

**Critical Path:** Implement stable scheduler scoring + atomic commit → wire synchronous stats → validate enrichment deltas → lock API contracts → freeze for demo.

---

## 💡 Final Architecture Notes
- **Reliability > Perfection:** A stable, predictable 80% system outperforms a brittle 100% optimizer in competition judging.
- **Mathematical Soundness:** Plan vs. Delta separation ensures enrichment converges to real user behavior without drift.
- **Zero Black Boxes:** Every module is deterministic, auditable, and gracefully degrades under load or ML failure.
- **Demo-Ready by Design:** 10-day window, synchronous stats, atomic commits, and stability penalties guarantee reproducible, judge-friendly behavior.