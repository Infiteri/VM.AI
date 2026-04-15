# VM.AI Backend — Conversation Summary & Context Handoff
**Date:** April 13, 2026
**Current Stage:** API Schemas & Validation Complete. Services (Matcher/Enrichment) Next.

---

## 1. Architectural Decisions Made
- **Draft Table Pattern:** We introduced `task_drafts` to handle the "Chat → Commit" flow safely. The frontend receives a `draft_id` after parsing and sends it back on commit. This prevents "Zombie Tasks" if the user closes the browser.
- **No Predicted Flags in API:** We decided **not** to send `predicted` flags to the frontend. The backend handles the logic internally by comparing the Draft data with the User's edits during the Commit phase.
- **Strict Validation:** All Schemas now use Pydantic `Field` with constraints (e.g., `difficulty` 0.0-1.0, `duration` < 1440).
- **Datetime Types:** All temporal fields (`start`, `deadline`, `fixed_start`) are now `datetime` types in the schema, ensuring automatic ISO validation.
- **Background Cleanup:** Added an async background task that runs every 24 hours to delete old drafts from the database.
- **Logging:** Configured `backend.log` to capture all events, while the console only shows warnings/errors.

## 2. API Changes
- **`POST /tasks`**: Now accepts an optional `draft_id`. 
    - If present: It executes the "Draft Commit" logic.
    - If absent: It executes the "Manual Creation" logic (Matcher → Enrichment → DB).
- **`GET /tasks/{id}`**: Added this endpoint to allow the frontend to fetch task details for modification.
- **`TaskPayload`**: `location` is now mandatory. `UnscheduledTaskItem` was replaced by `TaskDetailResponse`.

## 3. Current Code State
- **Schemas:** 100% Updated and Validated.
- **Endpoints:** Stubs updated to match new schemas.
- **Database:** Migrated to include `task_drafts` and normalized tables.
- **Next Step:** Implement `services/task_matcher.py` and `services/enrichment.py` to make the "Manual Creation" flow functional.

---
*End of Summary.*
