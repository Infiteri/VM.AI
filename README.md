# VM.AI - Natural Language Task Parser

VM.AI is an AI-driven personal scheduling system that transforms natural language task descriptions into structured, actionable task data. The system uses a fine-tuned T5-base model for structured parsing, a RidgeCV regressor for difficulty and importance prediction from text embeddings, and a rule-based parser for add mode — together extracting attributes such as category, difficulty, importance, duration, deadline, location, and recurrence patterns.

## Problem Description

The project addresses the challenge of converting free-form natural language input into structured task schemas. Users can describe tasks in plain language (e.g., "gym every Monday at 6am", "finish report by Friday"), and the system parses this input into organized data that can be used for scheduling and task management.

This aligns with ONIA competition requirements by providing a practical solution that uses AI to solve a real-world problem in task planning and time management.

## Team

- Golban Ion
- Furculita Maxim

## Project Structure

```
VM.AI/
├── src/
│   ├── parser/           # NLP parser module (training + inference)
│   ├── backend/          # FastAPI backend
│   │   └── tests/      # Backend API tests
│   └── app/              # React frontend (npm run dev)
├── models/
│   ├── finetuned_parser/ # Trained T5 model (after training)
│   └── regressors/       # RidgeCV diff/imp + XGBoost duration models
├── data/                 # Training datasets
├── tests/                # Parser test suite
├── scripts/              # Visualization and utility scripts
├── docs/                 # Detailed documentation
├── assets/               # Generated charts and visualizations
└── package.json          # Frontend dependencies
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

---

### Step 1: Pull Trained Model

```bash
cd VM.AI
python src/parser/pull_from_hf.py
```

This downloads the trained T5 model to `models/finetuned_parser/`.

---

### Step 2: Configure Database

1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE vmai_db;
   ```

2. Navigate to backend directory:
   ```bash
   cd src/backend
   ```

3. Copy the example environment file:
   ```bash
   copy .env.example .env    # Windows
   # cp .env.example .env    # Linux/Mac
   ```

4. Edit `.env` with your database credentials:
   ```
   DATABASE_URL=postgresql+psycopg://your_user:your_password@localhost:5432/vmai_db
   ```

---

### Step 3: Backend Setup

**Important**: This project uses `uv` - you do NOT need to manually activate virtual environments.

```bash
cd src/backend

# Install dependencies (creates .venv automatically)
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the backend server
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation with interactive testing will be available at: http://127.0.0.1:8000/docs

---

### Step 4: Frontend Setup

```bash
cd VM.AI

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at: http://localhost:5173

---

## Datasets

The T5 parser is trained on three datasets:

### 1. Synthetic Dataset (VMAI_SYNTHETIC_Data.yaml)

- Auto-generated training samples
- Created using template-based data generation
- Contains varied task descriptions with full schema coverage

### 2. Real Dataset (VMAI_REAL_Data.yaml)

- Human-written examples
- More natural language variations
- Includes both "add" and "modify" task patterns

### 3. Specific Dataset (VMAI_SPECIFIC_Data.yaml)

- Targeted examples for fields the model struggles with
- Focused on improving weak areas identified during evaluation

All T5 data follows the pipe-format schema with EXP/PRD tags:

- `[EXP]` - Explicit field (user stated the value directly)
- `[PRD]` - Predicted field (model inferred the value)

Two additional generated datasets support the ML services:

- **VMAI_REGR_Data.csv** — Task text with difficulty/importance labels, used to train the RidgeCV regressors
- **VMAI_DURATION_Data.csv** — Tabular features (difficulty, importance, scheduled duration, category, location, deadline) with real_duration labels, used to train the XGBoost duration model

## Training Pipeline

To retrain the model:

```bash
# From project root
python src/parser/train.py --mode [MODE]
```

Available modes:
- `both` - Mix of add and modify samples (recommended)
- `synthetic` - Only synthetic data
- `real` - Only real human examples
- `specific` - Targeted improvements
- `modify_only` - Modify pattern only (requires existing checkpoint)

Training produces metrics per field (category, difficulty, importance, duration, deadline, location, recurrence).

## Running the Chat Interface

For direct testing without the web interface:

```bash
python src/parser/chat.py
```

Commands:
- `add: <task description>` - Parse a new task
- `modify` - Modify the last added task
- `end` - Exit

## Testing

### Parser Tests (src/parser)

```bash
cd VM.AI

# Core parser functionality
python tests/test_core.py

# Data generation
python tests/test_generator.py

# Add/Modify mode parsing
python tests/test_add.py
python tests/test_modify.py

# Schema conversion
python tests/test_schemas.py

# Dataset validation
python tests/test_validate_dataset.py
python tests/test_data_no_duplicates.py
python tests/test_explicit_fields.py
```

### Backend API Tests (src/backend)

```bash
cd src/backend

# Run all backend tests
uv run pytest

# Individual test modules
uv run pytest tests/test_parser_service.py
uv run pytest tests/test_enrichment.py
uv run pytest tests/test_task_matching.py
uv run pytest tests/test_update_time_score.py
```

## Visualization

Generate charts and graphs for data analysis:

```bash
# Real dataset (7 plots → scripts/output/real/)
python scripts/plot_dataset.py --dataset real

# Specific dataset (7 plots → scripts/output/specific/)
python scripts/plot_dataset.py --dataset specific

# Synthetic dataset (8 plots → scripts/output/synthetic/)
python scripts/plot_synthetic.py

# Training metrics
python scripts/report.py
```

Generated visualizations are saved to `scripts/output/<dataset>/` and can be copied to `assets/` for documentation.

### Real Dataset

![Real Overview](assets/parser/real_overview.png)

### Specific Dataset

![Specific Overview](assets/parser/specific_overview.png)

### Synthetic Dataset

![Synthetic Overview](assets/parser/synthetic_overview.png)

## Documentation

Detailed documentation covering all project components is available in the `docs/` folder.

## Library Versions

Key dependencies:

- Python: 3.12+
- PyTorch: Latest (CUDA recommended for training)
- transformers: Latest (HuggingFace)
- datasets: Latest
- FastAPI: For backend
- SQLAlchemy: 2.0
- React: 19.x (frontend)
- Vite: 8.x (frontend build)

## Limitations and Ethical Considerations

### Data Limitations

- The model is trained on a limited dataset size
- Performance may vary for unusual or ambiguous task descriptions
- Category inference is based on keyword patterns; difficulty and importance are predicted by a RidgeCV regressor

### Technical Limitations

- The T5-base model has token limits that may affect complex inputs
- Rule-based parsers handle common patterns, edge cases may fail
- Time zone handling is not explicitly implemented

### Ethical Considerations

- No personal data is collected or stored by the parser
- The system uses synthetic and human-written data only
- No discrimination or bias is intentionally introduced in the model
- Results are presented objectively without manipulation
- All model outputs should be verified by users before critical use

### Model Risks

- Predicted fields (PRD) are inferred and may not always be accurate
- The model should not be used for critical decision-making without human oversight
- Duration is predicted by a separate XGBoost model on tabular features outside the parser pipeline

## Repository Structure

This repository follows best practices for AI projects:

- `/src` - Source code
- `/models` - Trained model files
- `/data` - Training data
- `/docs` - Documentation
- `/assets` - Visualizations and charts
- README.md - Complete project description with setup instructions

No personal or confidential data is included.

## References

- API Documentation: `docs/Frontend_API_Documentation.md`
- HuggingFace Model: vaneaa/vmai-parser
