# VM.AI Backend

AI-driven personal scheduling system backend for **ONIA 2026**.
Transforms natural language input into optimized, behavior-aware calendar schedules.

## 🛠 Tech Stack

- **Framework**: FastAPI (Async, Python 3.12+)
- **Database**: PostgreSQL 15+ (Native JSONB, UUID, Arrays)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic V2 (Strict types, ranges, model validators)
- **Migrations**: Alembic
- **Package Manager**: uv (Ultra-fast Python package installer)

---

## 📋 Prerequisites

1.  **Python 3.12+**
2.  **PostgreSQL 15+** (Running locally or accessible)
3.  **uv** (Python package manager)

---

## 🚀 Quick Start

### 1. Installation

Navigate to the backend directory:
```bash
cd src/backend
```

Install dependencies:
```bash
uv sync
```

### 2. Environment Configuration

Create a `.env` file in this directory (`src/backend/.env`) with your database credentials:

```env
# Database Configuration
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DB_NAME

# Server Configuration
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=true

# Scheduler Settings
SCHEDULER_TIMEOUT_SECONDS=12
```

### 3. Database Setup

Ensure your PostgreSQL database exists, then apply migrations:

```bash
uv run --active alembic upgrade head
```

*This creates all tables (Core, Workflow, Statistics, Drafts, Normalization).*

---

## 🏃 Running the Server

Start the development server with hot-reloading:

```bash
uv run --active uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **API Base URL**: `http://127.0.0.1:8000/api/v1`
- **Swagger UI (Docs)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📂 Project Structure

```text
src/backend/
├── app/
│   ├── core/           # Config, DB connection, Logging
│   ├── api/            # Routers & Endpoints
│   ├── models/         # SQLAlchemy ORM (DB Schema)
│   ├── schemas/        # Pydantic Models (Validation)
│   ├── services/       # Business Logic (NLP, Matcher, Enrichment, Scheduler)
│   └── utils/          # Helpers (Cleanup, Parsers)
├── alembic/            # Database Migration History
├── logs/               # Application Logs (backend.log)
└── .env                # Environment Variables (Create this!)
```

---

## 📝 Key Commands

### Database Migrations
```bash
# Generate new migration after model changes
uv run --active alembic revision --autogenerate -m "description"

# Apply migrations
uv run --active alembic upgrade head

# Check current version
uv run --active alembic current
```

### Testing
```bash
# Run tests (if implemented)
uv run pytest
```

---

## 📊 Logging

- **File**: Logs are saved to `logs/backend.log` (DEBUG level).
- **Console**: Only `WARNING` and `ERROR` messages are shown to keep the terminal clean.
- **Background**: The Garbage Collector runs every 24h to clean up abandoned drafts.

---

## ✅ Current Status

- [x] **Foundation**: Project setup, dependencies, environment.
- [x] **Database**: Schema v2.0, Migrations, Indexes.
- [x] **API Skeleton**: 13 Endpoints, Routing, CORS.
- [x] **Validation**: Strict Pydantic schemas, Model Validators.
- [x] **Utilities**: Logging, Background Cleanup.
- [ ] **Services**: Task Matcher, Enrichment, Scheduler (In Progress).

---

*Document prepared for ONIA 2026.*
