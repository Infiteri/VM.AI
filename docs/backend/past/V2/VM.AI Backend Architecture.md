---

# VM.AI Backend Architecture & Implementation Master Guide
**Competition:** ONIA 2026 | **Timeline:** 1 Month | **Stack:** FastAPI + PostgreSQL 15+ + SQLAlchemy + React  
**Document Purpose:** Deep architectural reference, concept explanation, and step-by-step implementation roadmap. Designed for learning, not blind copy-pasting.

---

## 🔐 1. Locked Constraints & Competition Rules
| Constraint | Why It Exists | Impact on Architecture |
|------------|---------------|------------------------|
| **v1.9 Database Schema** | State derived from table presence (`unscheduled_tasks` \| `provisional_schedule` \| `scheduled_slots`). No `status` field. | Eliminates state-sync bugs. Requires strict cascade rules and presence-based queries. |
| **v2.2 API Contracts** | 12 endpoints, unified `source` parameter, `{value, predicted}` structure, `"success": true` responses. | Guarantees frontend-backend parity. Enforces predictable request/response shapes. |
| **CPU-Only Inference** | Competition hardware limits. | Models must be lightweight. NLP (T5-base) and Matching (MiniLM) run synchronously with strict timeouts. |
| **Stable Incremental Scheduler** | Prevents schedule thrashing. Preserves user trust. | `O(N×15)` complexity, 12s hard timeout, 1-layer displacement max, 25% value threshold. |
| **Synchronous Stats Recorder** | Eliminates race conditions for MVP. | Runs in same DB transaction as triggering action. ~50ms overhead accepted. |
| **Atomic Commits** | Prevents blank calendar on network drop. | Single PostgreSQL transaction: `BEGIN → DELETE → INSERT ... SELECT → TRUNCATE → COMMIT`. |
| **PostgreSQL-Native Types** | Performance & type safety. | `UUID`, `JSONB`, `TEXT[]`, `FOR UPDATE SKIP LOCKED`. No MySQL/SQLite fallbacks. |

---

## 🏗️ 2. Architectural Philosophy: Why This Structure?

### 2.1 Separation of Concerns
Your project contains three distinct workloads:
1. **Frontend:** React/Vite (`src/app/`)
2. **AI Training/Parser:** Python scripts (`parser/`, `notebooks/`, `models/`)
3. **Backend API:** FastAPI (`src/backend/`)

Mixing these causes:
- Dependency conflicts (Node vs Python packages)
- Import path chaos (`from ... import` breaks)
- Deployment complexity
- Slower iteration (changing frontend breaks backend linting)

**Solution:** Isolate the backend in `src/backend/` with its own `uv` project, virtual environment, and configuration. The backend is a **stateless HTTP service** that talks to PostgreSQL and loads AI models on demand.

### 2.2 Layered Architecture Pattern
```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer                │
│  • Routers (endpoints/)                                     │
│  • Dependency Injection (get_db, auth, etc.)                │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP Request/Response
┌───────────────────────▼─────────────────────────────────────┐
│                    Validation Layer (Pydantic)              │
│  • Request/Response schemas                                 │
│  • Boundary validation (NLP → Enrichment handoff)           │
└───────────────────────┬─────────────────────────────────────┘
                        │ Validated Python Objects
┌───────────────────────▼─────────────────────────────────────┐
│                    Business Logic Layer (services/)         │
│  • NLP Parser → Task Matching → Enrichment → Scheduler → Stats │
│  • Pure Python, DB-agnostic where possible                  │
└───────────────────────┬─────────────────────────────────────┘
                        │ SQLAlchemy ORM Queries
┌───────────────────────▼─────────────────────────────────────┐
│                    Data Access Layer (models/)              │
│  • SQLAlchemy ORM mappings                                  │
│  • PostgreSQL-native types (UUID, JSONB, TEXT[])            │
└───────────────────────┬─────────────────────────────────────┘
                        │ SQL Execution
┌───────────────────────▼─────────────────────────────────────┐
│                    PostgreSQL Database                      │
│  • Core, Workflow, Statistics tables (v1.9)                 │
│  • Indexes, constraints, atomic transactions                │
└─────────────────────────────────────────────────────────────┘
```
**Why layers?** 
- Testability: You can mock the database when testing business logic.
- Maintainability: Changing a validation rule doesn't break database queries.
- Competition Safety: If NLP fails, validation catches it before it corrupts the DB.

---

## 📁 3. Complete Directory Structure & File Responsibilities

```
src/backend/
├── app/
│   ├── __init__.py                    # Marks directory as Python package
│   ├── main.py                        # FastAPI app factory, CORS, router aggregation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic-settings: DATABASE_URL, model paths, timeouts
│   │   ├── database.py                # SQLAlchemy engine, session factory, get_db dependency
│   │   └── exceptions.py              # Custom HTTPException handlers, error formatting
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── api.py                 # Aggregates all routers, applies /api/v1 prefix
│   │   │   ├── deps.py                # Dependency overrides (get_db, get_settings)
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── schedule.py        # GET /schedule, POST /schedule/batch
│   │   │       ├── tasks.py           # POST /tasks, DELETE /tasks/{id}, POST /tasks/parse/*
│   │   │       ├── provisional.py     # GET /provisional/changes, POST /commit, POST /reset
│   │   │       └── stats.py           # POST /tasks/{id}/rate
│   ├── models/                        # SQLAlchemy ORM (maps Python classes → DB tables)
│   │   ├── __init__.py
│   │   ├── base.py                    # Base class with id, created_at, updated_at
│   │   ├── task.py                    # tasks table
│   │   ├── schedule.py                # scheduled_slots, provisional_schedule
│   │   ├── workflow.py                # unscheduled_tasks, schedule_changes
│   │   └── statistics.py              # tasks_statistics, category_statistics
│   ├── schemas/                       # Pydantic models (request/response validation)
│   │   ├── __init__.py
│   │   ├── shared.py                  # UUID, Timestamp, Pagination helpers
│   │   ├── task.py                    # NLPField, ParsedTask, TaskCreateRequest
│   │   ├── schedule.py                # ScheduleResponse, ProvisionalChange
│   │   └── stats.py                   # RatingRequest, StatsUpdateResponse
│   ├── services/                      # Business logic (pipeline stages)
│   │   ├── __init__.py
│   │   ├── nlp_parser.py              # T5-base inference, add/modify modes
│   │   ├── task_matcher.py            # MiniLM embeddings, cosine similarity, thresholds
│   │   ├── enrichment.py              # Date resolution, historical averaging, DB writes
│   │   ├── scheduler.py               # Stable incremental algorithm, scoring, displacement
│   │   └── stats_recorder.py          # Synchronous updates, two-denominator math, radial decay
│   └── utils/                         # Pure functions, no side effects
│       ├── __init__.py
│       ├── date_parser.py             # Strict dateparser config (PREFER_FUTURE, RELATIVE_BASE)
│       ├── validation.py              # Pydantic boundary validators, regex fallback
│       └── logging.py                 # Structured boundary logs (NLP_DONE, ENRICHED, etc.)
├── alembic/                           # Database migration version control
│   ├── versions/                      # Auto-generated SQL migration scripts
│   ├── env.py                         # Alembic environment configuration
│   └── script.py.mako                 # Migration template
├── tests/                             # pytest suite
│   ├── conftest.py                    # Test DB fixture, async client, overrides
│   ├── test_api/                      # Endpoint integration tests
│   ├── test_services/                 # Pipeline unit tests
│   └── test_schemas/                  # Validation tests
├── alembic.ini                        # Alembic config (sqlalchemy.url)
├── pyproject.toml                     # uv project manifest, dependencies, scripts
├── uv.lock                            # Locked dependency tree (do not edit manually)
├── .env                               # Environment variables (DATABASE_URL, etc.)
└── .env.example                       # Template for teammates/judges
```

---

## 🧠 4. Core Technologies Explained (The "Why")

### 4.1 `uv` & Virtual Environments
- **What it is:** A modern Python project manager & package resolver. `uv venv` creates an isolated environment.
- **Why use it:** Prevents your FastAPI dependencies from conflicting with React build tools or PyTorch training scripts. Each environment has its own `site-packages`.
- **How it works:** `uv init` creates `pyproject.toml`. `uv add` installs packages into `uv.lock`. `uv run` executes commands using that environment's Python.

### 4.2 SQLAlchemy ORM vs Raw SQL
- **Raw SQL:** `SELECT * FROM tasks WHERE id = %s`
- **ORM:** `db.query(Task).filter(Task.id == task_id).first()`
- **Why ORM:** 
  - Type safety (IDE autocomplete, static analysis)
  - Automatic query parameterization (prevents SQL injection)
  - Easy relationship mapping (`task.scheduled_slots`)
  - Alembic autogeneration reads ORM classes to create migrations
- **When to use raw SQL:** Complex analytical queries, `INSERT ... SELECT`, or when you need exact control over execution plans. FastAPI supports both.

### 4.3 Pydantic Validation
- **What it is:** Data validation using Python type hints.
- **Why critical:** FastAPI automatically validates request bodies against Pydantic models. If frontend sends `{ "duration": "two hours" }`, Pydantic rejects it with `422 Validation Error` before it reaches your business logic.
- **Competition benefit:** Catches 80% of pipeline breaks at the boundary. Never crashes with `500` on malformed input.

### 4.4 Alembic Migrations
- **What it is:** Version control for your database schema.
- **Why you need it:** 
  - Teammates run `alembic upgrade head` to get the exact same schema.
  - Judges can reproduce your demo environment in 3 commands.
  - Rollback safely if a migration breaks: `alembic downgrade -1`
- **How it works:** You change an ORM model → run `alembic revision --autogenerate` → Alembic generates a Python script with `upgrade()` and `downgrade()` functions → `alembic upgrade head` applies it.

### 4.5 Dependency Injection (`get_db`)
- **What it is:** FastAPI's way of providing resources to route handlers.
- **Why use it:** Guarantees database connections are opened at request start and closed at response end, even if an error occurs.
```python
def get_db():
    db = SessionLocal()
    try:
        yield db  # Request happens here
    finally:
        db.close() # Always runs
```

### 4.6 CORS (Cross-Origin Resource Sharing)
- **What it is:** Browser security mechanism. Frontend (`localhost:5173`) cannot call Backend (`localhost:8000`) without explicit permission.
- **How it works:** FastAPI middleware adds `Access-Control-Allow-Origin` headers to responses.
- **Why critical:** Without it, your teammate's React app gets `CORS Error` in console and cannot fetch data.

---

## 🗄️ 5. Database Architecture & Migration Strategy

### 5.1 Table Groups & State Derivation
| Group | Tables | Purpose | State Logic |
|-------|--------|---------|-------------|
| **Core** | `tasks`, `scheduled_slots`, `provisional_schedule`, `schedule_changes` | Task definitions & calendar slots | Presence in table = state |
| **Workflow** | `unscheduled_tasks` | FIFO queue awaiting placement | Empty queue = all tasks scheduled |
| **Statistics** | `tasks_statistics`, `category_statistics` | Behavioral learning data | Never cascade-deleted. Persist for historical matching. |

**Critical Rule:** No `status` column. Query `WHERE task_id IN (SELECT task_id FROM unscheduled_tasks)` to find pending tasks.

### 5.2 Cascade Rules
- Core → Core: `ON DELETE CASCADE` (delete task → removes from schedule/queue)
- Core → Statistics: `ON DELETE NO ACTION` (statistics persist for future matching)
- Statistics → Core: No FK (read-only reference)

### 5.3 Migration Workflow
```bash
# 1. Change a model (e.g., add rated column)
# 2. Generate migration
alembic revision --autogenerate -m "add rated boolean to tasks"

# 3. Review generated file in alembic/versions/
# 4. Apply
alembic upgrade head

# 5. Verify
alembic current
```

---

## 🌐 6. API Design & FastAPI Fundamentals

### 6.1 Router Structure
```python
# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import schedule, tasks, provisional, stats

api_router = APIRouter()
api_router.include_router(tasks.router, tags=["Tasks"])
api_router.include_router(schedule.router, tags=["Schedule"])
api_router.include_router(provisional.router, tags=["Provisional"])
api_router.include_router(stats.router, tags=["Stats"])
```

### 6.2 Endpoint Pattern
```python
@router.post("/tasks", status_code=201, response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db)
):
    # 1. Validate (automatic via Pydantic)
    # 2. Business Logic (services/)
    # 3. DB Write (ORM)
    # 4. Return
    return TaskResponse(success=True, task_id=str(task.id), status="unscheduled")
```

### 6.3 Automatic Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Generated from type hints, docstrings, and Pydantic models. Zero manual writing.

---

## 🔁 7. The 5-Stage Pipeline: Deep Dive

### Stage 1: NLP Parser
- **Input:** `add: finish chemistry homework before Friday`
- **Process:** T5-base conditional generation → JSON parsing → Pydantic validation
- **Output:** `{ "name": {"value": "chemistry homework", "predicted": false}, ... }`
- **Why `predicted` flags?** Tells Enrichment which fields to override with historical data. `false` = user stated (immutable). `true` = model estimated (enrichable).

### Stage 2: Task Matching
- **Input:** Parsed task name
- **Process:** Exact case-insensitive match → MiniLM cosine similarity → Threshold classification
- **Thresholds:** `≥0.92` → `"same"`, `0.65–0.91` → `"similar"`, `<0.65` → `"none"`
- **Invariant:** `associated_id` points to `tasks_statistics.id`, never `tasks.id`.

### Stage 3: Enrichment
- **Input:** Parsed task + Match result
- **Process:** Resolve dates (`dateparser` strict config) → Apply historical averages → Calculate urgency/value → Create `tasks_statistics` row → Insert `tasks` → Add to `unscheduled_tasks`
- **Priority:** Matched task (`records≥3`) → Category stats → Cold start defaults (`0.5`)

### Stage 4: Scheduling Engine
- **Algorithm:** Constraint Solver → Top-15 Pruning → Stable Scoring → 1-Layer Displacement
- **Scoring:** `base + free_boost - stability_penalty + location + overlap + time_pref`
- **Guards:** 12s timeout, `<0.35` early termination, 25% value threshold for displacement
- **Output:** Writes to `provisional_schedule` + `schedule_changes`

### Stage 5: Stats Recorder
- **Execution:** Synchronous in same transaction
- **Two Denominators:** 
  - Plan averages → `records` (updated on commit)
  - Delta averages → `completed_count` (updated on rating)
- **Radial Decay:** `boost = base × (1 - blocks × 0.25)`, atomic JSONB update
- **Weekly Normalization:** `×0.99` cron job prevents saturation

---

## 🔗 8. Frontend-Backend Integration Pattern

### 8.1 Request Flow
```
React Component → fetch("http://localhost:8000/api/v1/tasks", {method: "POST", body: JSON})
                → FastAPI Router → Pydantic Validation → Service Pipeline → SQLAlchemy → PostgreSQL
                ← JSON Response ← FastAPI Response Model ← Service Return ← DB Commit
```

### 8.2 CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.3 Error Handling
- `422`: Validation error (Pydantic rejects malformed input)
- `404`: Resource not found (invalid UUID or missing task)
- `409`: Conflict (task already rated, duplicate scheduled)
- `500`: Server error (catch-all, log boundary, return safe message)

---

## 🔄 9. Development Workflow & Git Strategy

### 9.1 Branch Naming Convention
```
feature/nlp-parser
feature/stable-scheduler
fix/cascade-delete-logic
chore/alembic-migration-v1.9
```

### 9.2 Parallel Development Rules
1. **Frontend works against stubs first.** Backend returns deterministic mock data matching v2.2 shapes.
2. **Swap stubs incrementally.** Replace mock returns with real pipeline calls without changing response schemas.
3. **Never block UI.** If a module isn't ready, return fallback data. Real logic integrates seamlessly later.
4. **Log at boundaries.** `NLP_INPUT`, `ENRICHED`, `SCHEDULED`, `STATS_UPDATED` with timestamps.

### 9.3 Commit Message Format
```
<type>(scope): <subject>

feat(tasks): add NLP parse endpoint with Pydantic validation
fix(scheduler): cap displacement at 1 layer, add 12s timeout
docs(api): update swagger descriptions for source parameter
```

---

## 🗺️ 10. Step-by-Step Implementation Roadmap

### Week 1: Foundation & Safety
- [ ] Isolate `src/backend/` with `uv`
- [ ] Create FastAPI skeleton + CORS + health check
- [ ] Configure PostgreSQL + Alembic
- [ ] Generate v1.9 migration + apply indexes
- [ ] Implement `GET /schedule`, `GET /unscheduled`, `POST /tasks` stubs
- [ ] Share running URL with teammate

### Week 2: Core Pipeline & Math
- [ ] Implement NLP Parser + Pydantic boundary validation
- [ ] Build Task Matcher (MiniLM + cosine thresholds)
- [ ] Create Enrichment module (date resolution + historical averaging)
- [ ] Wire `POST /tasks` full pipeline
- [ ] Add regex fallback + error degradation

### Week 3: Scheduling & Workflow
- [ ] Implement Stable Incremental Scheduler
- [ ] Add 12s timeout + top-15 pruning + displacement rules
- [ ] Build `POST /schedule/batch`, `GET /provisional/changes`
- [ ] Implement atomic commit transaction
- [ ] Add `POST /provisional/reset`, `DELETE /tasks/{id}?source=...`

### Week 4: Stats, Polish & Freeze
- [ ] Wire Synchronous Stats Recorder (two-denominator math)
- [ ] Implement `POST /tasks/{id}/rate` + radial JSONB updates
- [ ] Pre-seed synthetic statistics for warm demo
- [ ] Performance test (50+ tasks batch scheduling)
- [ ] Freeze code 48h before demo. Record backup video.

---

## 💻 11. Essential CLI Reference

### Environment & Dependencies
```powershell
# Navigate to backend
cd src/backend

# Initialize project
uv init --name vm-ai-backend --no-workspace

# Create & activate venv
uv venv venv
.\venv\Scripts\Activate.ps1

# Add dependencies
uv add "fastapi[standard]" sqlalchemy alembic "psycopg[binary]" pydantic "pydantic-settings" python-dateutil sentence-transformers transformers

# Run server
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Database & Migrations
```bash
# Create database
createdb vmai_db

# Initialize Alembic
alembic init alembic

# Generate migration (after changing ORM models)
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

### Testing & Debugging
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_api/test_tasks.py -v

# Watch logs in real-time
uv run uvicorn app.main:app --reload --log-level debug
```

---

## ✅ 12. Competition Readiness Checklist

| Category | Item | Status |
|----------|------|--------|
| **Architecture** | Layered separation, isolated env, v1.9 schema locked | ⬜ |
| **Database** | PostgreSQL 15+, Alembic migrations, indexes applied | ⬜ |
| **API** | 12 endpoints match v2.2, automatic docs at `/docs` | ⬜ |
| **Pipeline** | NLP → Match → Enrich → Scheduler → Stats wired | ⬜ |
| **Safety** | Pydantic validation, 12s scheduler timeout, atomic commits | ⬜ |
| **Frontend Sync** | Stub endpoints match response shapes, CORS configured | ⬜ |
| **Demo Prep** | Synthetic stats seeded, fallback paths tested, video backup | ⬜ |
| **Code Freeze** | No new features 48h before demo. Only critical bug fixes | ⬜ |

---

## 📚 13. Learning Resources & Next Steps

### Recommended Reading
- **FastAPI Docs:** https://fastapi.tiangolo.com/ (Dependency Injection, Testing, Security)
- **SQLAlchemy 2.0:** https://docs.sqlalchemy.org/en/20/ (ORM, Core, Alembic)
- **Pydantic:** https://docs.pydantic.dev/latest/ (Validation, Settings, V2 migration)
- **PostgreSQL:** https://www.postgresql.org/docs/ (JSONB, Indexes, Transactions)

### Immediate Next Action
1. Save this file as `VM_AI_Backend_Architecture_Guide.md`
2. Run the CLI commands in Section 11 to initialize `src/backend/`
3. Reply `"Ready"` and I will generate the exact `app/main.py`, `core/config.py`, `core/database.py`, and Alembic configuration files with deep inline explanations.

You now have a complete architectural blueprint. Every decision is documented, every "why" is explained, and every step is competition-safe. Proceed deliberately. 🚀