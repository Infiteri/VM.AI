# NLP Parser — Technical Documentation
**Version:** 1.0 (Final)
**Last Updated:** April 18, 2026
**Competition:** ONIA 2026

---

## 1. Overview

The NLP Parser is the entry point of the entire VM.AI pipeline. It transforms raw, conversational user input into a clean, structured `TaskPayload` object that downstream modules can reliably consume.

### Key Design Principles
- **Draft Pattern**: Parsed tasks are saved to `task_drafts` table with a `draft_id`. Frontend edits data, then commits with `draft_id`. Prevents database pollution.
- **Date Passthrough**: Raw date strings (`"Friday"`, `"next Monday 3pm"`) are intentionally left unparsed. Date resolution is handled by the Enrichment module.
- **CPU-optimized**: Uses fine-tuned T5-base, balancing accuracy with lightweight inference suitable for competition deployment.
- **Strict boundary validation**: Output is validated against `TaskPayload` schema before passing to Task Matching/Enrichment.

### What It Does
- Handles two operations: `Add` (full extraction) and `Modify` (delta extraction)
- Prefixes inputs to switch model modes (`add:` / `modify:`)
- Outputs `TaskPayload` object with clean types (datetime, float, int)
- Passes raw temporal strings to Enrichment for resolution
- Saves enriched draft to `task_drafts` table

### What It Does NOT Do
- Parse dates or resolve relative time references
- Handle task deletion (managed directly by backend)
- Update main database tables (only writes to `task_drafts`)

---

## 2. Position in Pipeline

```
User Input (Chat or Form)
    ↓
NLP Parser → TaskPayload object
    ↓
Task Matching → {name_vector, associated_id, association_status}
    ↓
Enrichment → resolves dates, applies historical averages
    ↓
Save to task_drafts → Return draft_id to frontend
    ↓
User reviews/edits → Frontend sends draft_id + edits
    ↓
Commit Endpoint → Moves from drafts to main DB
```

---

## 3. Operations

### 3.1 Add Mode
Triggered when the user creates a new task.

**Input Format:**
```
add: finish chemistry homework before Friday, pretty hard
```

**Behavior:**
- Extracts `name`, `deadline`, `difficulty`, `duration`, `category`, `location`, `importance`
- Sets `fixed_time: false`, `start: null`, `fixed_start: null`
- Runs Task Matching + Enrichment to compute hidden fields
- Saves complete draft to `task_drafts` table
- Returns `draft_id` + `TaskPayload` to frontend

### 3.2 Modify Mode
Triggered when the user edits an existing task. The model receives the full current task JSON alongside the change prompt.

**Input Format:**
```
modify: {"name": "chemistry homework", "deadline": "Friday", "duration": 75} | make it 2 hours and push deadline to Sunday
```

**Behavior:**
- Compares prompt against existing JSON context
- Returns delta JSON containing only modified fields
- Preserves original values for unchanged fields

### 3.3 Delete
Handled entirely by the backend. No NLP inference required.

---

## 4. Output Schema

Returns a `TaskPayload` object with clean types:

```json
{
    "name": "Chemistry homework",
    "start": "2026-04-20T09:00:00",
    "deadline": "2026-04-24T17:00:00",
    "difficulty": 0.7,
    "duration": 60,
    "category": ["study"],
    "location": "Library",
    "importance": 0.6,
    "fixed_time": false,
    "fixed_start": null
}
```

---

## 5. Date Handling

The parser preserves raw date strings for Enrichment to resolve:

| Parser Output | Enrichment Input | Final Output |
|--------------|-----------------|--------------|
| `"Friday"` | dateparser → `"2026-04-24T17:00:00"` | datetime |
| `"next Monday"` | dateparser → `"2026-04-21T09:00:00"` | datetime |
| `"tomorrow 3pm"` | dateparser → `"2026-04-19T15:00:00"` | datetime |

---

## 6. Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| Malformed output | Model produces invalid JSON | Retry with fallback |
| No fields detected | Empty input | Return minimal payload |
| Token overflow | Input too long | Truncate and warn |

---

## 7. Model Details

| Property | Value |
|----------|-------|
| Base Model | T5-base |
| Fine-tuned | Yes (domain-specific) |
| Max Input Tokens | 256 |
| Max Output Tokens | 128 |
| Inference Speed | ~100ms on CPU |

---

## 8. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Convert natural language to TaskPayload |
| **Modes** | Add, Modify |
| **Output** | Clean TaskPayload with {value, predicted} structure |
| **Date Handling** | Passthrough to Enrichment |
| **Storage** | task_drafts table |
| **Next Stage** | Task Matching |

---

*Document prepared for ONIA 2026.*