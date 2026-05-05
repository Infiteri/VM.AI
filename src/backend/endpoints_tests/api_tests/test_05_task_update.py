"""
API Edge Cases: POST /tasks/{id}/update
=======================================
Tests edge cases for updating tasks.

# Depends on: Workflow tests ran first
# Run after: test_03_unscheduled.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestUpdateTaskEdgeCases:
    """
    Edge case tests for update endpoint.
    """
    
    def test_update_past_task_rejected(self, client, db, log_base_dir, clean_test_data):
        """Test: Update a task that ended in the past."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Look for tasks scheduled in the past
        from datetime import date, timedelta
        from app.models import MainScheduleSlot, Task
        
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = client.get(f"/api/v1/schedule?date={yesterday}")
        
        if response.status_code != 200:
            pytest.skip("Could not query schedule")
        
        tasks = response.json().get("tasks", [])
        past_task = tasks[0] if tasks else None
        
        if not past_task:
            pytest.skip("No past tasks to test")
        
        task_id = past_task.get("task_id")
        
        before = tracker.snapshot()
        response = client.post(
            f"/api/v1/tasks/{task_id}/update?source=main_schedule",
            json={"task": {"name": "Modified"}}
        )
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_05_task_update",
            test_name="past_task_rejected",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/update",
            input_data={"source": "main_schedule"},
            response=response,
            db_changes=changes
        )
        
        # Should return 400 for past task
        if response.status_code == 400:
            assert "ended in the past" in response.json().get("detail", "")
            print("Past task rejected: 400")
        else:
            print(f"Past task update: {response.status_code}")
    
    def test_update_invalid_source(self, client, db, log_base_dir, clean_test_data):
        """Test: Update with invalid source."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Create a task first
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": "TEST_UPDATE_INVALID"})
        if parse_resp.status_code != 200:
            pytest.skip("Could not parse")
        
        task_data = parse_resp.json().get("task", {})
        create_resp = client.post("/api/v1/tasks/", json={
            "task": task_data,
            "draft_id": parse_resp.json().get("draft_id")
        })
        
        if create_resp.status_code != 201:
            pytest.skip("Could not create")
        
        task_id = create_resp.json().get("task_id")
        
        before = tracker.snapshot()
        response = client.post(
            f"/api/v1/tasks/{task_id}/update?source=invalid",
            json={"task": {"name": "Modified"}}
        )
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_05_task_update",
            test_name="invalid_source",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/update",
            input_data={"source": "invalid"},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 400
        print("Invalid source: 400")
