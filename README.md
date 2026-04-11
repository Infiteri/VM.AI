# VM.AI
VM.AI is the project for ONIA built by
- Golban Ion
- Furculiță Maxim

The project, as of writing README.md, features the basic UI + parser training module

## Training
```
git clone https://github.com/Infiteri/VM.AI --depth 1
cd VM.AI
uv venv .venv
.venv/Scripts/activate
(.venv) python src/parser/train.py --mode [MODE]
```

Where '[MODE]' is the training mode, each training mode is configured in
config.yaml, however the data builder can only extract from a few mods (i.e. both, specific, real)

## Testing

The test suite validates every layer of the parser — from low-level pipe-format parsing to end-to-end chat interactions.

### Full Suite

```
(.venv) python tests/test_llm_full.py
```

Runs all 4 core test suites (`test_core`, `test_generator`, `test_add`, `test_modify`) sequentially and prints a pass/fail summary.

### Component Tests

**Core Parser** — validates pipe-format string parsing, field prediction flags (`[EXP]` vs `[PRD]`), and change-detection logic between old/new schemas.
```
(.venv) python tests/test_core.py
```

**Data Generator** — validates the synthetic data generator's keyword-based inference for category, difficulty, importance, duration, and location.
```
(.venv) python tests/test_generator.py
```

**Add Mode** — tests the `TaskPlannerPredictor` on natural-language task creation, verifying field extraction (category, difficulty, importance, duration, fixed_time, recurrent, location).
```
(.venv) python tests/test_add.py
```

**Modify Mode** — tests task modification: rescheduling, duration changes, priority shifts, category reassignment, and deadline updates.
```
(.venv) python tests/test_modify.py
```

### Regression & Sanitization

**Chat Suite** — runs a before/after regression by feeding a fixed set of add and modify prompts through `chat.py`, capturing outputs to `test_results_before.json` for comparison after model changes.
```
(.venv) python tests/test_chat_suite.py
```

**Sanitization** — comprehensive pre-training check that validates schema tag generation (`[EXP]`/`[PRD]`), data generator output format, validation logic, keyword detection, normalization functions, and real data integrity across 10 test sections.
```
(.venv) python tests/test_sanitize.py
```

### Interactive Chat

```
(.venv) python src/parser/chat.py
```

Launches the interactive chat loop for manual add/modify testing.

## Visualization Scripts

All scripts render dark-themed PNGs into `scripts/output/`. They require `matplotlib`, `seaborn`, and `pandas`.

### Dataset Analysis

**Full dataset overview** — generates a multi-panel figure: category pie chart, difficulty vs importance scatter (colored by category), duration histogram, add/modify split bar chart, and a stats summary table.
```
(.venv) python scripts/visualize_dataset.py <path_to_yaml>
```

**Combined categories** — loads both synthetic and real datasets, plots category distributions, difficulty, importance, and duration histograms side by side.
```
(.venv) python scripts/plot_categories.py
```

**Real data overview** — visualizes only `VMAI_REAL_Data.yaml` with a scatter plot, box plot (duration by category), and category pie chart.
```
(.venv) python scripts/plot_real.py
```

**Specific fixes** — visualizes `VMAI_SPECIFIC_Data.yaml` to verify targeted dataset improvements (importance gap fill, difficulty/importance scatter).
```
(.venv) python scripts/plot_specific.py
```

**Scatter — difficulty vs importance** — standalone scatter plot of real data points colored by category, with per-category point counts.
```
(.venv) python scripts/plot_scatter.py
```

### Training Monitoring

**Training loss** — reads `models/finetuned_parser/trainer_log.jsonl` and plots train/eval loss curves over training steps. Requires a completed training run.
```
(.venv) python scripts/plot_training.py
```

## Documentation

| Document | Description |
|---|---|
| [Project Overview](docs/VM.AI_Full_Project_Overview_v1.md) | Full project overview and architecture |
| [NLP Parser](docs/NPL_Parser_v1.md) | Parser module documentation |
| [Database Schema](docs/Database_Schema_v1.md) | Database schema reference |
| [Task Matching](docs/Task_Matching_Module_v1.md) | Task matching module |
| [Scheduling Engine](docs/Scheduling_Engine_v1.md) | Scheduling engine documentation |
| [Enrichment Module](docs/Enrichment_module_v1.md) | Data enrichment module |
| [Stats Recorder](docs/Stats_Recorder_v1.md) | Statistics recording module |
| [Model Accuracy](docs/current_model_accuracy.md) | Current model accuracy metrics |
| [Risks](docs/Risks.md) | Project risks and considerations |


