```markdown
# NLP Parser — Technical Documentation
VM.AI Project · ONIA 2026
Version 3.0 (Stable Pipeline Integration)

## 1. Overview

The NLP Parser is the entry point of the entire VM.AI pipeline. It transforms raw, conversational user input into a clean, structured JSON object that downstream modules can reliably consume.

### Key Design Principles
- **Predicted flags**: Every field carries a `predicted` boolean to signal whether the value came explicitly from the user or was estimated by the model.
- **Date passthrough**: Raw date strings (`"Friday"`, `"next Monday 3pm"`) are intentionally left unparsed. Date resolution is handled by the Enrichment module.
- **CPU-optimized**: Uses fine-tuned T5-base, balancing accuracy with lightweight inference suitable for competition deployment.
- **Strict boundary validation**: Output is validated before passing to Task Matching/Enrichment to prevent pipeline corruption.

### What It Does
- Handles two operations: `Add` (full extraction) and `Modify` (delta extraction)
- Prefixes inputs to switch model modes (`add: <prompt>` / `modify: <json> | <prompt>`)
- Outputs JSON with per-field `predicted` flags
- Catches malformed outputs and returns structured error responses
- Passes raw temporal strings to Enrichment for resolution

### What It Does NOT Do
- Parse dates or resolve relative time references
- Handle task deletion (managed directly by backend)
- Make scheduling, enrichment, or matching decisions
- Update any database tables
- Process recurring task templates (out of scope)

## 2. Position in Pipeline

```text
User Input (Chat or Form)
↓
NLP Parser → structured JSON + predicted flags
↓
Boundary Validation (Pydantic schema)
↓
Task Matching → {associated_id, name_vector, association_status}
↓
Enrichment → resolves dates, applies historical averages, writes to DB
↓
Unscheduled Tasks (stored in DB)
```

## 3. Key Concepts

| Concept | Description |
|---------|-------------|
| `predicted: false` | User stated this explicitly. Enrichment will **never** override. |
| `predicted: true` | Model estimated this. Enrichment **may** replace with historical data. |
| Mode Prefix | T5 requires explicit mode switches: `add:` vs `modify: <existing_json> \| <change>` |
| Date Passthrough | Raw strings preserved (`"Friday"`, `"tonight"`). Enrichment uses `dateparser`. |
| Token Budget | Max 256 input / 128 output tokens. Truncation risk logged, not silently ignored. |

## 4. Operations

### 4.1 Add
Triggered when the user creates a new task. The model extracts all detectable fields from a single prompt.

**Input Format:**
```text
add: finish chemistry homework before Friday, pretty hard
```

**Behavior:**
- Extracts `name`, `deadline`, `difficulty`, `duration`, `category`, `location`, `importance`
- Sets `fixed_time: false`, `start: null`, `recurrent: false`
- Marks explicitly stated fields as `predicted: false`, estimated fields as `predicted: true`

### 4.2 Modify
Triggered when the user edits an existing task. The model receives the full current task JSON alongside the change prompt, and outputs **only the fields that changed**.

**Input Format:**
```text
modify: {"name": "chemistry homework", "deadline": "Friday", "duration": 75, ...} | make it 2 hours and push deadline to Sunday
```

**Behavior:**
- Compares prompt against existing JSON context
- Returns delta JSON containing only modified fields
- Preserves original `predicted` status for unchanged fields (handled downstream)
- Converts fixed ↔ flexible tasks when explicitly requested

### 4.3 Delete
Handled entirely by the backend. No NLP inference required. User selects task → presses Delete → cascade removes from core tables (statistics preserved).

## 5. Output Schema

Every field follows the `{ "value": <type>, "predicted": bool }` structure.

```json
{
  "name":            { "value": "string",          "predicted": false },
  "start":           { "value": "string | null",   "predicted": false },
  "deadline":        { "value": "string | null",   "predicted": false },
  "difficulty":      { "value": float (0.0–1.0),   "predicted": true },
  "duration":        { "value": int (minutes),     "predicted": true },
  "category":        { "value": ["string"],        "predicted": true },
  "location":        { "value": "string",          "predicted": true },
  "importance":      { "value": float (0.0–1.0),   "predicted": true },
  "fixed_time":      { "value": bool,              "predicted": false },
  "fixed_start":     { "value": "string | null",   "predicted": false },
  "recurrent":       { "value": bool,              "predicted": false },
  "recurrence_days": { "value": ["string"] | null, "predicted": false }
}
```

> 💡 **Fixed-Time Tasks**: When `fixed_time: true`, `start` and `deadline` are `null`. Only `fixed_start` contains a raw time string (e.g., `"Monday 09:00"`).
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
    if "name" not in result or result["name"]["value"] is None:
        raise ValueError("missing name field")
except (json.JSONDecodeError, ValueError) as e:
    result = {"error": "parse_failed", "raw": model_output, "reason": str(e)}
```

### 8.2 Pydantic Boundary Validation (Concrete)
All outputs pass through a strict schema validator before Task Matching.
```python
from pydantic import BaseModel, validator

class NLPField(BaseModel):
    value: object
    predicted: bool

class ParsedTask(BaseModel):
    name: NLPField
    duration: NLPField
    difficulty: NLPField
    category: NLPField
    # ... other fields
    
    @validator('duration', 'difficulty', pre=True)
    def coerce_numeric(cls, v):
        if isinstance(v.get('value'), str):
            raise ValueError(f"Expected numeric, got string: {v['value']}")
        return v
```
If validation fails, the system returns a user-friendly prompt: `"Please rephrase your request. I couldn't extract the task details."`

### 8.3 Cold Start & Fallback
- If the model fails to load or returns consistent parse errors, a lightweight regex-based fallback extracts `name`, `duration`, and `deadline` using keyword patterns.
- Fallback marks all fields as `predicted: true` to force Enrichment to apply defaults or category averages.

## 9. Cold Start Behavior

When a new user has no history:
- Model operates identically (trained on synthetic + general examples)
- `predicted: true` fields will default to model estimates
- Enrichment applies category-level averages or `0.5` cold-start defaults
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

## 11. Summary

| Aspect | Description |
|--------|-------------|
| **Purpose** | Transform natural language into structured JSON with predicted flags |
| **Model** | Fine-tuned T5-base (220M params, ~900MB) |
| **Operations** | `Add` (full extraction), `Modify` (delta extraction), `Delete` (backend-only) |
| **Date Handling** | Raw strings passed through. Resolved by Enrichment module. |
| **Output Schema** | `{ "value": <type>, "predicted": bool }` per field |
| **Predicted Flags** | `false` = explicit (never overridden), `true` = estimated (may be enriched) |
| **Token Limits** | 256 input / 128 output. Logged warning if exceeded. |
| **Validation** | JSON parse + Pydantic schema enforcement before pipeline handoff |
| **Fallback** | Regex keyword extractor + safe defaults if ML fails |
| **Cold Start** | Works immediately. Relies on model training + category defaults. |
| **Recurring Tasks** | NOT IMPLEMENTED — documented as future scope |
| **AI Content** | Fine-tuned transformer. Training data: synthetic (1x), real (2x), specific (1x) |
```