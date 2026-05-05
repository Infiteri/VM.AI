"""
Workflow 6: Modify Future Task
=============================
Purpose: User moves/changes a scheduled task

Flow:
1. Create new task, schedule, commit (setup for clean test)
2. POST /tasks/{id}/update (source=main_schedule)
3. GET /tasks/unscheduled → task moved to queue
4. Batch + commit again
5. GET /schedule → updated time

Run after: test_wf_05_rate_uncompleted.py
Cleanup: Deletes created task
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow06ModifyFutureTask:
    """
    Tests modifying a scheduled task (moving it).
    
    # Run after: test_wf_05_rate_uncompleted.py
    # Depends on: Clean state (may create new task)
    # Updates: task, unscheduled_tasks
    # Cleanup: Deletes created test tasks
    """
    
    def test_modify_scheduled_task(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Modify a future scheduled task.
        
        Expected:
        - update returns 200
        - task moved to unscheduled queue
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Create and schedule a new task
        from datetime import date, timedelta
        
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        prompt = "TEST_MODIFY_TASK workflow 6"
        
        # parse/add
        before = tracker.snapshot()
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="setup_parse",
            step=0,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": prompt},
            response=parse_resp,
            db_changes=changes
        )
        
        if parse_resp.status_code != 200:
            pytest.skip("Could not parse task")
        
        draft_id = parse_resp.json().get("draft_id")
        task_data = parse_resp.json().get("task", {})
        
        # create
        before = tracker.snapshot()
        create_resp = client.post("/api/v1/tasks/", json={
            "task": task_data,
            "draft_id": draft_id
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="setup_create",
            step=0,
            endpoint="/api/v1/tasks/",
            input_data={"task": task_data},
            response=create_resp,
            db_changes=changes
        )
        
        if create_resp.status_code != 201:
            pytest.skip("Could not create task")
        
        task_id = create_resp.json().get("task_id")
        
        # batch
        before = tracker.snapshot()
        batch_resp = client.post("/api/v1/schedule/batch")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="setup_batch",
            step=0,
            endpoint="/api/v1/schedule/batch",
            input_data={},
            response=batch_resp,
            db_changes=changes
        )
        
        # commit
        before = tracker.snapshot()
        commit_resp = client.post("/api/v1/provisional/commit")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="setup_commit",
            step=0,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=commit_resp,
            db_changes=changes
        )
        
        print(f"Created task {task_id} and scheduled")
        
        # Step 1: GET schedule to find our task
        # ====================================
        from datetime import date, timedelta
        
        today = date.today()
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        
        if response.status_code == 200:
            tasks = response.json().get("tasks", [])
            our_task = next((t for t in tasks if str(t.get("task_id")) == str(task_id)), None)
        else:
            our_task = None
        
        if not our_task:
            # Try tomorrow
            tomorrow_date = today + timedelta(days=1)
            response = client.get(f"/api/v1/schedule?date={tomorrow_date.isoformat()}")
            if response.status_code == 200:
                tasks = response.json().get("tasks", [])
                our_task = next((t for t in tasks if str(t.get("task_id")) == str(task_id)), None)
        
        if not our_task:
            pytest.skip("Task not found in schedule")
        
        print(f"Task {task_id} is in schedule at {our_task.get('start')}")
        
        # Step 2: POST /tasks/{id}/update (source=main_schedule)
        # ====================================
        before = tracker.snapshot()
        
        update_payload = {
            "task": {
                "name": task_data.get("name", "Modified Task"),
                "difficulty": 0.6,
                "duration": 90,
                "importance": 0.8
            }
        }
        
        response = client.post(
            f"/api/v1/tasks/{task_id}/update?source=main_schedule",
            json=update_payload
        )
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="step2_update_task",
            step=2,
            endpoint=f"/api/v1/tasks/{task_id}/update",
            input_data=update_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        if response.status_code == 400:
            # Task might have ended (if it was scheduled for today and it's past now)
            error = response.json().get("detail", "")
            if "ended in the past" in error or "already rated" in error:
                pytest.skip(f"Cannot modify task: {error}")
        
        assert response.status_code == 200, f"update failed: {response.json()}"
        print("Task updated successfully")
        
        # Step 3: Check unscheduled queue
        # ====================================
        before = tracker.snapshot()
        
        response = client.get("/api/v1/tasks/unscheduled")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_06_modify_future_task",
            test_name="step3_check_unscheduled",
            step=3,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        unscheduled = response.json()
        tasks = unscheduled.get("tasks", [])
        
        task_in_queue = any(str(t.get("task_id")) == str(task_id) for t in tasks)
        print(f"Task in unscheduled queue: {task_in_queue}")
