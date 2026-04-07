# NLP Parser - Accuracy Check
Date: 2026-04-06
Version: 0.1.3 (post-both, 7 epochs)

## Verdict: MODEL NOT TRAINED — All outputs are ~0.3 diff / ~0.5 imp

Every test produces the same broken values. The training script resumed from
old corrupted checkpoints instead of starting fresh from t5-base.

## Add Results (14 tests)

| Input | Field | Expected | Got | Status |
|-------|-------|----------|-----|--------|
| gym at 6am | fixed_start | 06:00 | 6:30 | ❌ Wrong time format |
| gym at 6am | category | fitness | **work** | ❌ Wrong |
| meditate every morning | category | health | **work** | ❌ Wrong |
| meditate every morning | recurrent | true | **false** | ❌ Wrong |
| pay the rent | category | finance | home | ❌ Wrong |
| pay the rent | importance | >0.8 | 0.5 | ❌ Too low |
| file the taxes | category | finance | work | ❌ Wrong |
| file the taxes | importance | >0.8 | 0.55 | ❌ Too low |
| hard workout | category | fitness | fitness | ✅ |
| hard workout | difficulty | >0.7 | **0.3** | ❌ All stuck at 0.3 |
| easy stretch | difficulty | <0.3 | **0.3** | ❌ All stuck at 0.3 |
| easy stretch | category | fitness | **work** | ❌ Wrong |
| urgent client call | importance | >0.7 | **0.55** | ❌ All stuck at ~0.5 |
| critical crash fix | difficulty | >0.7 | **0.3** | ❌ All stuck at 0.3 |
| low priority cleanup | importance | <0.4 | **0.55** | ❌ All stuck at ~0.5 |
| study at library 2h | duration | 120 | **60** | ❌ "2 hours" not parsed |
| study at library 2h | location | library | - | ❌ Not extracted |
| grocery shopping | category | shopping | home | ❌ Wrong |
| team meeting 3pm | fixed_start | 15:00 | 15:00 | ✅ |
| book flight | category | travel | travel | ✅ |
| write blog post | category | creative | creative | ✅ |

### Scorecard
- Category: 3/14 (21%) — only fitness, travel, creative correct
- Difficulty: 0/14 (0%) — all stuck at ~0.3
- Importance: 0/14 (0%) — all stuck at ~0.5
- Duration: 0/14 (0%) — ignores "2 hours", defaults to 45-60
- Fixed time: 1/3 (33%) — "3pm" correct, "6am" wrong (6:30)
- Recurrence: 0/1 (0%) — "every morning" not detected
- Location: 0/2 (0%) — "at the library" not extracted

## Root Cause
Training script loaded `finetuned_parser` folder which contained old checkpoints
from previous failed runs. It saw "7 epochs complete" and stopped immediately
without retraining. The model.safetensors file is still the corrupted one.

## Required Fix
1. Delete entire `models/finetuned_parser` folder (not just checkpoints)
2. Verify it's gone: `dir models/` should show only `google-t5`
3. Run: `python src/parser/train.py --mode both`
4. First output line must show `LR: 2e-05` (fresh), NOT `LR: 5e-06` (resume)
