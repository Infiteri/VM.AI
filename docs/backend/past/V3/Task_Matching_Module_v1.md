# Task Matching Model — Technical Documentation
VM.AI Project · ONIA 2026
Version 2.4 (Stable Pipeline Integration)
Last Updated: April 13, 2026

## 1. Overview

The Task Matching Model is the second stage in the VM.AI pipeline. Its job is to compare the task name parsed by the NLP module against every task name stored in the user's `tasks_statistics` table and determine whether the new task is the **same** as an existing one, **similar**, or **entirely new**.

This distinction is critical because the Enrichment module uses the match result to decide:
- Which `associated_task_statistics_id` to store in the `tasks` table
- Where to read historical averages from (matched task's row vs. category row)

### What It Does
- Encodes the parsed task name into a 384-dimensional semantic vector
- Performs exact case-insensitive string matching first
- Falls back to cosine similarity against all stored task vectors
- Classifies the relationship using fixed thresholds
- Returns a lightweight, deterministic payload for Enrichment

### What It Does NOT Do
- Modify task data or update the database
- Access user history, completion rates, or behavioral profiles
- Make scheduling, enrichment, or stats-recording decisions
- Require fine-tuning or training — used entirely off-the-shelf

## 2. Position in Pipeline

```text
User Input
↓
NLP Parser → TaskPayload
↓
Task Matching Model → { name_vector, associated_id, association_status }
↓
Boundary Validation (Pydantic schema enforcement)
↓
Enrichment Module → reads tasks_statistics or category_statistics
↓
Enrichment → creates tasks_statistics row (if needed)
↓
Enrichment → creates tasks row with both ID fields
↓
Enrichment → inserts task_id into unscheduled_tasks
```

## 3. Model Details

| Property | Value |
|----------|-------|
| Model Name | `paraphrase-MiniLM-L6-v2` |
| Framework | HuggingFace `sentence-transformers` |
| Vector Size | 384 dimensions |
| Inference Speed | ~5ms per sentence on CPU |
| Disk Size | ~90MB |
| Training Required | No — used off-the-shelf |
| ONIA Compliance | Yes — fully open-source, documented, CPU-only |

## 4. Matching Algorithm

The matcher follows a strict, deterministic two-step process to maximize speed and accuracy.

### Step 1: Exact String Match (Pre-filter)
- Case-insensitive, whitespace-trimmed comparison against all `task_name` values in `tasks_statistics`
- If a match is found → immediately return `association_status: "same"`
- **Why first?** Eliminates unnecessary vector computation for exact duplicates (~30% of user inputs)

### Step 2: Semantic Similarity (Cosine Distance)
If no exact match:
1. Encode parsed task name → `input_vector` (shape: `[384]`)
2. Compute cosine similarity against every stored `task_name_vector` in `tasks_statistics`
3. Identify highest similarity score (`best_score`)
4. Classify using fixed thresholds:
   - `best_score >= 0.92` → `"same"`
   - `0.65 <= best_score < 0.92` → `"similar"`
   - `best_score < 0.65` → `"none"`

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
```

> 💡 **Single-User Scale Note:** Cosine similarity against all rows is `O(N)` where `N` = number of tasks. For a personal productivity tool, `N` rarely exceeds 500–1000. Vectorized NumPy computation completes in `<2ms`.

## 5. Output Schema

The model always returns exactly three fields. This is the **only** payload passed to Enrichment.

| Field | Type | Description |
|-------|------|-------------|
| `name_vector` | `float[384]` | Encoded vector of the parsed task name. Stored in `tasks_statistics.task_name_vector`. |
| `associated_id` | `UUID \| null` | `tasks_statistics.id` of the best matching task. `null` when `association_status = "none"`. |
| `association_status` | `"same" \| "similar" \| "none"` | Classification result based on thresholds. |

```json
{
  "name_vector": [0.23, -0.11, 0.45, 0.89, ...],
  "associated_id": "550e8400-e29b-41d4-a716-446655440000",
  "association_status": "same"
}
```

## 6. Match Cases & Enrichment Handoff

The Enrichment module consumes this output to determine database writes and data source priority.

| `association_status` | New `tasks_statistics` row? | `task_statistics_id` | `associated_task_statistics_id` | Enrichment Data Source |
|----------------------|-----------------------------|----------------------|----------------------------------|------------------------|
| `"same"` | **No** | `= associated_id` | `= associated_id` | Matched task's row (if `records >= 3`) |
| `"similar"` | **Yes** | New UUID | `= associated_id` | Matched task's row (if `records >= 3`) |
| `"none"` | **Yes** | New UUID | `null` | Category-level statistics |

> ⚠️ **Critical Invariant:** `associated_id` is always a `tasks_statistics.id`, never a `tasks.id`. This points directly to the statistics row, enabling clean separation between task instances and behavioral history.

## 7. Threshold Configuration

Thresholds are hardcoded as constants but should be exposed via environment variables for easy tuning during demo preparation.

| Constant | Default Value | Meaning |
|----------|---------------|---------|
| `EXACT_THRESHOLD` | `0.92` | `≥ 0.92` → `"same"` |
| `SIMILAR_THRESHOLD` | `0.65` | `0.65–0.91` → `"similar"` |
| Fallback | `< 0.65` | `"none"` |

**Tuning Guidance:**
- Too high → fails to recognize paraphrases (`"chem hw"` vs `"chemistry homework"`)
- Too low → incorrectly merges unrelated tasks (`"gym workout"` vs `"buy groceries"`)
- Adjust during Week 3 using real user logs before demo day.

## 8. Database Reference

The Task Matching Model only **reads** from `tasks_statistics`. It does not write.

| Table | Field | Purpose |
|-------|-------|---------|
| `tasks_statistics` | `id` | Returned as `associated_id` |
| `tasks_statistics` | `task_name` | Used for exact string pre-filter |
| `tasks_statistics` | `task_name_vector` | 384-dim embedding for cosine similarity |

> ℹ The `tasks_statistics` table also contains statistical fields (`avg_duration`, `records`, etc.), but the matcher **ignores them completely**. Separation of concerns is strict.

## 9. Vector Storage Lifecycle

While the matcher computes `name_vector`, storage happens during the database commit phase (handled by Enrichment/backend):

1. NLP parses task → passes name to matcher
2. Matcher returns `{ name_vector, associated_id, association_status }`
3. Enrichment uses result to determine DB writes
4. Backend inserts `name_vector` into `tasks_statistics.task_name_vector` during task creation
5. Vector is never recomputed or updated unless the task name is modified (handled via separate pipeline path)

## 10. Cold Start Behavior

When a new user has zero task history:
- `tasks_statistics` table is empty (except pre-seeded categories)
- Exact match loop returns no results
- Cosine similarity list is empty → `best_score = 0.0`
- Returns: `association_status: "none"`, `associated_id: null`, `name_vector: [computed]`
- Enrichment falls back to category-level statistics immediately
- System works from first input. No warmup period required.

## 11. Implementation Recommendations & Proposals

The following proposals are strongly recommended to ensure reliability, prevent silent mismatches, and maximize demo-day performance:

| Area | Proposal | Impact |
|------|----------|--------|
| **Environment Thresholds** | Load `EXACT_THRESHOLD` and `SIMILAR_THRESHOLD` from `.env` | Enables quick tuning during demo without code changes |
| **Batch Similarity Optimization** | Use `sentence-transformers.util.cos_sim` for vectorized comparison | Reduces Python loop overhead, keeps `<5ms` even at 500+ tasks |
| **Pydantic Output Validation** | Wrap matcher return in strict schema before passing to Enrichment | Catches type/format mismatches early, prevents pipeline crashes |
| **Name Normalization** | Strip punctuation, collapse multiple spaces, lowercase before exact match | Prevents false negatives on `"Math HW!"` vs `"math hw"` |
| **Fallback on Model Load Failure** | If `sentence-transformers` fails to initialize, return `association_status: "none"` with logged warning | Guarantees pipeline never blocks on dependency issues |

## 12. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Classify new task name against existing history |
| **Model** | `paraphrase-MiniLM-L6-v2` (384-dim, off-the-shelf) |
| **Matching Order** | Exact string → Cosine similarity → Threshold classification |
| **Thresholds** | `≥ 0.92` = same, `0.65–0.91` = similar, `< 0.65` = none |
| **Output** | `{ name_vector, associated_id, association_status }` |
| `associated_id` Type | `tasks_statistics.id` (never `tasks.id`) |
| **DB Interaction** | Read-only on `tasks_statistics` (id, task_name, task_name_vector) |
| **Cold Start** | Returns `"none"` immediately. Works from first input. |
| **Vector Storage** | Handled during backend commit, not inside matcher |
| **AI Content** | Semantic embedding only. No fine-tuning, no training loops. |
| **Execution** | Synchronous, lightweight (`<10ms` end-to-end) |
| **Next Stage** | Enrichment Module (uses payload to select historical data source) |
