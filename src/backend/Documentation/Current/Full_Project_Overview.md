# VM.AI — Full Project Overview
**Competition:** ONIA 2026
**Status:** Architecture Complete, Services In-Progress

---

## 1. Core Value Proposition
VM.AI is an AI-driven personal scheduling system that transforms natural language input into optimized, behavior-aware calendar schedules. It prioritizes **schedule stability** and **predictable performance**.

---

## 2. 5-Stage Pipeline

1.  **NLP Parser:** T5-base model extracts task fields from text.
2.  **Task Matching:** MiniLM embeddings + Cosine Similarity to link tasks to history.
3.  **Enrichment:** Resolves dates and applies historical averages.
4.  **Scheduler:** Stable Incremental Algorithm (12s timeout, 1-layer displacement).
5.  **Stats Recorder:** Synchronous updates of behavioral metrics.

---

## 3. Key Features
- **Draft System:** Safe task creation via Chat without polluting the main database.
- **Strict Validation:** API enforces ranges and types strictly to prevent runtime errors.
- **Atomic Commits:** Prevents blank calendar on network drop.
- **Background Cleanup:** Auto-deletes abandoned drafts every 24 hours.

---
*Document prepared for ONIA 2026.*
