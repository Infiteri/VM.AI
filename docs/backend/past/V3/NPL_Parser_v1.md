# NLP Parser — Technical Documentation
VM.AI Project · ONIA 2026
Version 3.0 (Stable Pipeline Integration + Draft Pattern)
Last Updated: April 13, 2026

## 1. Overview

The NLP Parser is the entry point of the entire VM.AI pipeline. It transforms raw, conversational user input into a clean, structured `TaskPayload` object that downstream modules can reliably consume.

### Key Design Principles
- **Draft Pattern**: Parsed tasks are saved to `task_drafts` table with a `draft_id`. Frontend edits data, then commits with `draft_id`. Prevents database pollution.
- **Date passthrough**: Raw date strings (`"Friday"`, `"next Monday 3pm"`) are intentionally left unparsed. Date resolution is handled by the Enrichment module.
- **CPU-optimized**: Uses fine-tuned T5-base, balancing accuracy with lightweight inference suitable for competition deployment.
- **Strict boundary validation**: Output is validated against `TaskPayload` schema before passing to Task Matching/Enrichment to prevent pipeline corruption.
- **No predicted flags**: The API returns clean data. Backend handles enrichment logic internally by comparing draft data with user edits.

### What It Does
- Handles two operations: `Add` (full extraction) and `Modify` (delta extraction)
- Prefixes inputs to switch model modes (`add: <prompt>` / `modify: <json> | <prompt>`)
- Outputs `TaskPayload` object with clean types (datetime, float, int)
- Catches malformed outputs and returns structured error responses
- Passes raw temporal strings to Enrichment for resolution
- Saves enriched draft to `task_drafts` table for later commit

### What It Does NOT Do
- Parse dates or resolve relative time references
- Handle task deletion (managed directly by backend)
- Make scheduling, enrichment, or matching decisions
- Update main database tables (only writes to `task_drafts`)
- Process recurring task templates (out of scope)

## 2. Position in Pipeline

```text
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

## 3. Key Concepts

| Concept | Description |
|---------|-------------|
| **Draft Pattern** | Parsed tasks saved temporarily in `task_drafts`. Frontend edits, then commits with `draft_id`. |
| **Mode Prefix** | T5 requires explicit mode switches: `add:` vs `modify: <existing_json> \| <change>` |
| **Date Passthrough** | Raw strings preserved (`"Friday"`, `"tonight"`). Enrichment uses `dateparser`. |
| **Token Budget** | Max 256 input / 128 output tokens. Truncation risk logged, not silently ignored. |
| **Clean Output** | Returns `TaskPayload` with strict types. No predicted flags in API response. |

## 4. Operations

### 4.1 Add
Triggered when the user creates a new task. The model extracts all detectable fields from a single prompt.

**Input Format:**
```text
add: finish chemistry homework before Friday, pretty hard
```

**Behavior:**
- Extracts `name`, `deadline`, `difficulty`, `duration`, `category`, `location`, `importance`
- Sets `fixed_time: false`, `start: null`, `fixed_start: null`
- Runs Task Matching + Enrichment to compute hidden fields
- Saves complete draft to `task_drafts` table
- Returns `draft_id` + `TaskPayload` to frontend

### 4.2 Modify
Triggered when the user edits an existing task. The model receives the full current task JSON alongside the change prompt, and outputs **only the fields that changed**.

**Input Format:**
```text
modify: {"name": "chemistry homework", "deadline": "Friday", "duration": 75, ...} | make it 2 hours and push deadline to Sunday
```

**Behavior:**
- Compares prompt against existing JSON context
- Returns delta JSON containing only modified fields
- Preserves original values for unchanged fields
- Converts fixed ↔ flexible tasks when explicitly requested
- Saves updated draft to `task_drafts` table

### 4.3 Delete
Handled entirely by the backend. No NLP inference required. User selects task → presses Delete → cascade removes from core tables (statistics preserved).

## 5. Output Schema

Returns a `TaskPayload` object with clean types. Every field is strictly typed and validated.

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

> 💡 **Fixed-Time Tasks**: When `fixed_time: true`, `start` and `deadline` are `null`. Only `fixed_start` contains a datetime value.
> 💡 **Recurrent Tasks**: `NOT IMPLEMENTED` for ONIA 2026. Fields remain in schema for future expansion but are ignored by downstream modules.

## 6. Model & Training

### 6.1 Architecture
| Property | Value |
|----------|-------|
| Base Model | T5-base (`google-t5/t5-base`) |
| Parameters | 220M |
| Model Size | ~900MB |
| Inference Time | ~1.0s CPU / ~0.2s GPU |
| Framework | PyTorch + HuggingFace Transformers |

### 6.2 Training Strategy
| Dataset | Purpose | Weight |
|---------|---------|--------|
| `VMAI_SYNTHETIC_Data.yaml` | Template-generated variety, covers all field combinations | 1x |
| `VMAI_REAL_Data.yaml` | Hand-written realistic examples, teaches natural phrasing | 2x (duplicated) |
| `VMAI_SPECIFIC_Data.yaml` | Edge cases & known failure patterns, targeted fixes | 1x |

### 6.3 Training Parameters
| Parameter | Value |
|-----------|-------|
| Max Input Length | 256 tokens |
| Max Output Length | 128 tokens |
| Epochs | 5 |
| Batch Size | 16 per device |
| Optimizer | Adafactor |
| Learning Rate (Fresh) | 2e-5 |
| Learning Rate (Resume) | 5e-6 |

Training supports three modes: `--mode synthetic` (fast iteration), `--mode real` (fix phrasing), `--mode both` (full run).

## 7. Token Limits & Constraints

| Constraint | Value | Handling |
|------------|-------|----------|
| Input Tokens | Max 256 | Logged warning if exceeded. Safe limit: ~400 characters. |
| Output Tokens | Max 128 | Hard cap. If output truncates, JSON validation will fail and trigger fallback. |
| Context Window | Standard T5 | Modify prompts include full task JSON + change instruction. Must stay under 256. |

> 💡 **Best Practice for Demo**: Frontend displays a subtle character counter (~380 chars = safe). Prevents truncation before inference.

## 8. Error Handling & Boundary Validation

### 8.1 JSON Parse Validation
Catches malformed model outputs before they reach downstream modules.
```python
try:
    result = json.loads(model_output)
    if "name" not in result or result["name"] is None:
        raise ValueError("missing name field")
except (json.JSONDecodeError, ValueError) as e:
    result = {"error": "parse_failed", "raw": model_output, "reason": str(e)}
```

### 8.2 Pydantic Boundary Validation (Concrete)
All outputs pass through a strict schema validator before Task Matching.
```python
from pydantic import BaseModel, Field

class TaskPayload(BaseModel):
    name: str = Field(..., min_length=1)
    duration: int = Field(..., gt=0, lt=1440)
    difficulty: float = Field(..., gt=0.0, le=1.0)
    category: List[str] = Field(..., min_length=1)
    # ... other fields with strict validation

    @model_validator(mode='after')
    def check_fixed_logic(self):
        # Enforces flexible vs fixed task rules
        ...
```
If validation fails, the system returns a user-friendly prompt: `"Please rephrase your request. I couldn't extract the task details."`

### 8.3 Cold Start & Fallback
- If the model fails to load or returns consistent parse errors, a lightweight regex-based fallback extracts `name`, `duration`, and `deadline` using keyword patterns.
- Fallback forces Enrichment to apply defaults or category averages.
- Draft is still saved to `task_drafts` for user review.

## 9. Cold Start Behavior

When a new user has no history:
- Model operates identically (trained on synthetic + general examples)
- Enrichment applies category-level averages or `0.5` cold-start defaults
- Draft is saved with computed fields
- No warmup period required. System works from first input.

## 10. Implementation Recommendations & Proposals

The following proposals are strongly recommended to ensure reliability, prevent silent failures, and maximize demo-day performance:

| Area | Proposal | Impact |
|------|----------|--------|
| **Pydantic Boundary Validation** | Enforce schema between NLP and Task Matching. Reject/fix type mismatches early. | Catches 80% of silent pipeline breaks before Enrichment math operations |
| **Token Limit Monitoring** | Log input/output token counts per request. Alert if >90% of budget used. | Prevents silent truncation, helps tune prompts for demo |
| **Confidence Heuristic** | Add simple confidence scoring based on output token probability or attention entropy. | Enables UI hints like `"Low confidence on duration. Verify?"` for high-stakes fields |
| **Date String Normalization** | Ensure all raw date strings passed to Enrichment are stripped of trailing punctuation/whitespace. | Prevents `dateparser` ambiguity on messy user input |
| **Fallback Regex Parser** | Keep lightweight `re`-based extractor as backup if ML service crashes or times out. | Guarantees system never shows "500 Error" to judges or users |
| **FastAPI Middleware Logging** | Log `NLP_INPUT`, `NLP_OUTPUT`, `NLP_VALIDATION_PASS`, `NLP_LATENCY_MS` at request boundaries. | Enables real-time debugging during live demos |
| **Draft Cleanup** | Background async task runs every 24h to delete old drafts. | Prevents database pollution from abandoned tasks |

## 11. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Transform natural language into structured TaskPayload with draft_id |
| **Model** | Fine-tuned T5-base (220M params, ~900MB) |
| **Operations** | `Add` (full extraction), `Modify` (delta extraction), `Delete` (backend-only) |
| **Date Handling** | Raw strings passed through. Resolved by Enrichment module. |
| **Output Schema** | `{ draft_id: UUID, task: TaskPayload }` |
| **Token Limits** | 256 input / 128 output. Logged warning if exceeded. |
| **Validation** | JSON parse + Pydantic schema enforcement before pipeline handoff |
| **Fallback** | Regex keyword extractor + safe defaults if ML fails |
| **Cold Start** | Works immediately. Relies on model training + category defaults. |
| **Recurring Tasks** | NOT IMPLEMENTED — documented as future scope |
| **AI Content** | Fine-tuned transformer. Training data: synthetic (1x), real (2x), specific (1x) |
| **Draft Pattern** | Saves to task_drafts, returns draft_id, cleanup after 24h |
```
