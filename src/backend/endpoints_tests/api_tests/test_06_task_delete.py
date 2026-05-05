"""
API Edge Cases: DELETE /tasks/{id}
==================================
Tests edge cases for deleting tasks.

# Depends on: Workflow tests ran first
# Run after: test_08_rate_task.py
"""
import pytest
from uuid import uuid4
from helpers import DBChangeTracker, TestHelper


class TestDeleteTaskEdgeCases:
    """
    Edge case tests for delete endpoint.
    """
    
    def test_delete_nonexistent_uuid(self, client, db, log_base_dir, clean_test_data):
        """Test: Delete with fake UUID."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        fake_id = str(uuid4())
        
        before = tracker.snapshot()
        response = client.delete(f"/api/v1/tasks/{fake_id}?source=main_schedule")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_06_task_delete",
            test_name="nonexistent_uuid",
            step=1,
            endpoint=f"/api/v1/tasks/{fake_id}",
            input_data={"source": "main_schedule"},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 404
        print("Nonexistent UUID: 404")
    
    def test_delete_invalid_source(self, client, db, log_base_dir, clean_test_data):
        """Test: Delete with invalid source parameter."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # First create a task
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": "TEST_DELETE_INVALID"})
        if parse_resp.status_code != 200:
            pytest.skip("Could not create task")
        
        task_id = parse_resp.json().get("task", {}).get("name")
        
        # Get actual task ID
        from app.models import Task
        task = db.query(Task).filter(Task.name.like('%TEST_DELETE_INVALID%')).first()
        if not task:
            pytest.skip("Task not found")
        
        before = tracker.snapshot()
        response = client.delete(f"/api/v1/tasks/{task.id}?source=invalid_source")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_06_task_delete",
            test_name="invalid_source",
            step=1,
            endpoint=f"/api/v1/tasks/{task.id}",
            input_data={"source": "invalid_source"},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 400
        print("Invalid source: 400")
    
    def test_delete_invalid_uuid_format(self, client, db, log_base_dir, clean_test_data):
        """Test: Delete with invalid UUID format."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.delete("/api/v1/tasks/not-a-uuid?source=tasks")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_06_task_delete",
            test_name="invalid_uuid_format",
            step=1,
            endpoint="/api/v1/tasks/not-a-uuid",
            input_data={"source": "tasks"},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Invalid UUID format: 422")
