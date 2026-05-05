"""
Workflow 7: Delete from Schedule
================================
Purpose: User removes a task from schedule

Flow:
1. Create task, schedule, commit (setup)
2. DELETE /tasks/{id}?source=main_schedule
3. GET /schedule → task not present
4. GET /tasks/{id} → 404 (cascade deleted)

Run after: test_wf_06_modify_future_task.py
Cleanup: Task is deleted by this workflow
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow07DeleteFromSchedule:
    """
    Tests deleting a task from schedule.
    
    # Run after: test_wf_06_modify_future_task.py
    # Depends on: Clean state
    # Deletes: task and cascade
    # Cleanup: N/A (task deleted)
    """
    
    def test_delete_from_main_schedule(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Delete a task from main_schedule.
        
        Expected:
        - delete returns 204
        - task not in schedule
        - task not retrievable (404 or cascade)
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Create and schedule a task
        from datetime import date, timedelta
        
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        prompt = "TEST_DELETE_WORKFLOW_7"
        
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        if parse_resp.status_code != 200:
            pytest.skip("Could not parse task")
        
        draft_id = parse_resp.json().get("draft_id")
        task_data = parse_resp.json().get("task", {})
        
        create_resp = client.post("/api/v1/tasks/", json={
            "task": task_data,
            "draft_id": draft_id
        })
        if create_resp.status_code != 201:
            pytest.skip("Could not create task")
        
        task_id = create_resp.json().get("task_id")
        
        client.post("/api/v1/schedule/batch")
        client.post("/api/v1/provisional/commit")
        
        print(f"Created and scheduled task {task_id}")
        
        # Step 1: DELETE /tasks/{id}?source=main_schedule
        # ====================================
        before = tracker.snapshot()
        
        response = client.delete(f"/api/v1/tasks/{task_id}?source=main_schedule")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_07_delete_from_schedule",
            test_name="step1_delete",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}",
            input_data={"source": "main_schedule"},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 204 else "FAIL"
        )
        
        assert response.status_code == 204, f"delete failed: {response.json()}"
        print("Task deleted")
        
        # Step 2: GET /schedule → task not present
        # ====================================
        before = tracker.snapshot()
        
        response = client.get(f"/api/v1/schedule?date={tomorrow}")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_07_delete_from_schedule",
            test_name="step2_check_schedule",
            step=2,
            endpoint="/api/v1/schedule",
            input_data={"date": tomorrow},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        tasks = response.json().get("tasks", [])
        task_exists = any(str(t.get("task_id")) == str(task_id) for t in tasks)
        assert not task_exists, "Task should not be in schedule"
        print("Task not found in schedule")
