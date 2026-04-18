# VM.AI — Risk Register & Mitigation Strategies
**Version:** 3.0 (Final)
**Last Updated:** April 18, 2026
**Competition:** ONIA 2026

---

## 1. Overview

This document consolidates all architectural, data-integrity, and implementation risks identified during VM.AI development. Each risk includes explanation, impact, and mitigation.

---

## 2. Tier 1: Critical Risks

### 2.1 Non-Atomic Schedule Commit
**Risk:** Commit steps copy `provisional_schedule → main_schedule` using separate SQL. If network drops mid-commit, main schedule can be wiped.

**Impact:** User clicks "Commit" → gets blank calendar. Demo fails.

**Mitigation:** Use single PostgreSQL transaction:
```sql
BEGIN;
  DELETE FROM main_schedule;
  INSERT INTO main_schedule SELECT * FROM provisional_schedule;
  TRUNCATE schedule_changes;
COMMIT;
```

### 2.2 Stats Recorder Concurrency
**Risk:** Race conditions with async stats updates causing delta drift.

**Impact:** Running averages use stale values, Enrichment uses wrong baselines.

**Mitigation:** Run Stats Recorder **synchronously** in same request as commit/rating.

### 2.3 Scheduler Timeout & Branch Explosion
**Risk:** Combinatorial search space causes 5-15+ second latency.

**Impact:** UI freezes, batch scheduling fails.

**Mitigation:**
- Hard timeout: `if elapsed > 12s: break`
- Early termination: `if score < 0.35: skip`
- Top-15 candidate pruning

### 2.4 Draft Table Pollution
**Risk:** Abandoned drafts consume storage indefinitely.

**Impact:** Database grows with zombie tasks.

**Mitigation:** Background cleanup runs every 24 hours:
```sql
DELETE FROM task_drafts WHERE created_at < NOW() - INTERVAL '24 hours';
```

---

## 3. Tier 2: High Priority Risks

### 3.1 NLP Output Type Errors
**Risk:** T5 outputs wrong types (`"duration": "two hours"`).

**Impact:** Pipeline crashes with 500 error.

**Mitigation:** Pydantic validation at NLP → Enrichment boundary.

### 3.2 Time Preference Saturation
**Risk:** Scores cap at 10.0, freeze learning after ~1 week.

**Impact:** System ignores new user behavior.

**Mitigation:** Weekly ×0.99 decay via cron job.

### 3.3 Missing Database Indexes
**Risk:** Schedule overlap checks use full table scans.

**Impact:** Performance degrades as schedule fills.

**Mitigation:**
```sql
CREATE INDEX idx_provisional_range ON provisional_schedule (start, end);
CREATE INDEX idx_main_schedule_range ON main_schedule (start, end);
CREATE INDEX idx_unscheduled_fifo ON unscheduled_tasks (created_at);
```

### 3.4 Denominator Logic Confusion
**Risk:** Using wrong counters for plan vs delta averages.

**Impact:** Mathematical drift.

**Mitigation:**
- Plan averages (updated on commit): `records`
- Delta averages (updated on rating): `completed_count`

---

## 4. Tier 3: Medium Priority Risks

### 4.1 Date Parser Ambiguity
**Risk:** `dateparser` may interpret dates incorrectly.

**Impact:** Tasks land in wrong time windows.

**Mitigation:** Use strict settings:
```python
dateparser.parse(raw, settings={
    "PREFER_DATES_FROM": "future",
    "RELATIVE_BASE": datetime.now()
})
```

### 4.2 Cold Start Defaults
**Risk:** New users see "unintelligent" recommendations.

**Impact:** Demo appears broken.

**Mitigation:** Pre-seed category_statistics with 3-5 synthetic tasks.

---

## 5. Scheduler Architecture

### Why Stable Incremental?
| Aspect | CP-SAT | Stable Incremental |
|-------|--------|-----------------|
| Rewrites schedule | Yes | No |
| User trust | Low | High |
| Complexity | Exponential | O(N × 15) |
| DB changes | Yes | No |

### Core Stability Rules

| Rule | Implementation |
|------|----------------|
| Stability Penalty | `score -= 0.20` if displaced |
| Free Slot Boost | `score += 0.15` |
| Displacement Threshold | Don't displace if value diff < 25% |
| Max Displacement | 1 layer only |
| Timeout | 12 seconds hard limit |

---

## 6. Implementation Status

| Component | Status |
|----------|--------|
| Database Schema | Complete |
| API Contracts | Complete |
| NLP Parser | Complete |
| Task Matching | Complete |
| Enrichment | Complete |
| Scheduler | Not implemented |
| Stats Recorder | Not implemented |
| Atomic Commit | Not implemented |
| Background Cleanup | Not implemented |

---

## 7. Remaining Work

### High Priority
- Implement atomic commit transaction
- Add database indexes
- Implement background cleanup

### Medium Priority
- Pre-seed synthetic statistics
- Add logging at pipeline boundaries

### Low Priority
- Implement scheduler
- Implement stats recorder

---

## 8. Execution Timeline

| Week | Focus |
|------|-------|
| 1 | Foundation |
| 2 | Core Pipeline |
| 3 | Demo Readiness |
| 4 | Polish & Freeze |

---

*Document prepared for ONIA 2026.*