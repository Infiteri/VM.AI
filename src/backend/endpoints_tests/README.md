# API Endpoint Tests

Comprehensive test suite for VM.AI backend API endpoints.

## Structure

```
endpoints_tests/
├── conftest.py                 # pytest configuration
├── helpers.py                  # Shared test utilities
├── workflows/                  # Integration tests (user journeys)
│   ├── test_wf_01_add_task_to_queue.py
│   ├── test_wf_02_schedule_unscheduled.py
│   ├── test_wf_03_commit_schedule.py
│   ├── test_wf_04_rate_completed.py
│   ├── test_wf_05_rate_uncompleted.py
│   ├── test_wf_06_modify_future_task.py
│   ├── test_wf_07_delete_from_schedule.py
│   ├── test_wf_08_reset_provisional.py
│   ├── test_wf_09_parse_and_modify.py
│   └── test_wf_10_full_lifecycle.py
├── api_tests/                  # Edge case tests
│   ├── test_01_parse_add.py
│   ├── test_02_parse_modify.py
│   ├── test_03_unscheduled.py
│   ├── test_04_task_create.py
│   ├── test_05_task_update.py
│   ├── test_06_task_delete.py
│   ├── test_07_task_get.py
│   ├── test_08_rate_task.py
│   ├── test_09_11_provisional.py
│   ├── test_12_schedule_get.py
│   └── test_13_schedule_batch.py
└── logs/                      # Test results
    ├── workflows/
    └── api/
```

## Running Tests

### Run all tests
```bash
cd c:\VM.AI\src\backend
python -m pytest endpoints_tests -v
```

### Run only workflow tests
```bash
python -m pytest endpoints_tests/workflows -v
```

### Run only API edge case tests
```bash
python -m pytest endpoints_tests/api_tests -v
```

### Run a specific test file
```bash
python -m pytest endpoints_tests/workflows/test_wf_01_add_task_to_queue.py -v
```

### Run a specific test
```bash
python -m pytest endpoints_tests/workflows/test_wf_01_add_task_to_queue.py::TestWorkflow01AddTaskToQueue::test_user_adds_gym_task -v
```

## Test Execution Order

Tests run in this order:

1. **Workflow tests (1-10)** - Integration tests simulating real user journeys
   - wf_01: Add task to queue
   - wf_02: Schedule unscheduled tasks
   - wf_03: Commit schedule
   - wf_04: Rate completed task
   - wf_05: Rate uncompleted task
   - wf_06: Modify future task
   - wf_07: Delete from schedule
   - wf_08: Reset provisional
   - wf_09: Parse and modify
   - wf_10: Full lifecycle

2. **API edge case tests (11+)** - Unit tests for edge cases
   - test_01: parse/add edge cases
   - test_02: parse/modify edge cases
   - test_03: unscheduled edge cases
   - test_04: task create edge cases
   - test_05: task update edge cases
   - test_06: task delete edge cases
   - test_07: task get edge cases
   - test_08: rate task edge cases
   - test_09/11: provisional endpoints
   - test_12: schedule get edge cases
   - test_13: schedule batch edge cases

## Test Logs

Each test logs its results to JSON files:

- **Workflow logs**: `endpoints_tests/logs/workflows/test_wf_XX.json`
- **API logs**: `endpoints_tests/logs/api/test_XX.json`

### Log Format

```json
{
    "timestamp": "2026-05-05T10:30:00",
    "test_file": "test_wf_01_add_task_to_queue",
    "test_name": "step1_parse_add",
    "step": 1,
    "endpoint": "/api/v1/tasks/parse/add",
    "input": {"prompt": "go to gym tomorrow at 6pm"},
    "response": {
        "status_code": 200,
        "body": {"draft_id": "...", "task": {...}}
    },
    "db_changes": [
        {
            "table": "task_drafts",
            "action": "INSERT",
            "record": {"id": "...", "name": "go to gym..."}
        }
    ],
    "result": "PASS"
}
```

## Test Helpers

### DBChangeTracker
Captures DB state before/after API calls and computes changes.

```python
tracker = DBChangeTracker(db)
before = tracker.snapshot()
# ... call API ...
after = tracker.snapshot()
changes = tracker.compute_changes(before, after)
```

### TestHelper
Logs test results and provides cleanup utilities.

```python
helper = TestHelper()
helper.log_result(log_dir, test_file, test_name, step, endpoint, input, response, changes)
helper.cleanup_task(db, task_id)
```

## Cleanup

Each workflow test cleans up after itself:
- Workflows delete created test tasks
- API tests use `clean_test_data` fixture to clean up test prefixes

## Coverage

| Endpoint | Workflow Tests | Edge Case Tests |
|----------|---------------|-----------------|
| POST /tasks/parse/add | ✓ | ✓ |
| POST /tasks/parse/modify | ✓ | ✓ |
| GET /tasks/unscheduled | ✓ | ✓ |
| POST /tasks | ✓ | ✓ |
| POST /tasks/{id}/update | ✓ | ✓ |
| DELETE /tasks/{id} | ✓ | ✓ |
| GET /tasks/{id} | ✓ | ✓ |
| POST /tasks/{id}/rate | ✓ | ✓ |
| GET /provisional/changes | ✓ | ✓ |
| POST /provisional/reset | ✓ | ✓ |
| POST /provisional/commit | ✓ | ✓ |
| GET /schedule | ✓ | ✓ |
| POST /schedule/batch | ✓ | ✓ |

**Total: 52 tests**

## Notes

- Tests use an in-memory SQLite database for isolation
- Each test gets a fresh database session
- Workflow tests depend on prior workflows (e.g., wf_02 needs wf_01 to run first)
- Edge case tests assume workflows have run and created some data
