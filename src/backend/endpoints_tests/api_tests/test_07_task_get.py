"""
API Edge Cases: GET /tasks/{id}
================================
Tests edge cases for getting task details.

# Depends on: Workflow tests ran first
# Run after: test_05_task_update.py
"""
import pytest
from uuid import uuid4
from helpers import DBChangeTracker, TestHelper


class TestGetTaskEdgeCases:
    """
    Edge case tests for get task endpoint.
    """
    
    def test_get_nonexistent_task(self, client, db, log_base_dir, clean_test_data):
        """Test: Get task with fake UUID."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        fake_id = str(uuid4())
        
        before = tracker.snapshot()
        response = client.get(f"/api/v1/tasks/{fake_id}")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_07_task_get",
            test_name="nonexistent",
            step=1,
            endpoint=f"/api/v1/tasks/{fake_id}",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 404
        print("Nonexistent task: 404")
    
    def test_get_invalid_uuid_format(self, client, db, log_base_dir, clean_test_data):
        """Test: Get task with invalid UUID format."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.get("/api/v1/tasks/not-a-uuid")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_07_task_get",
            test_name="invalid_uuid",
            step=1,
            endpoint="/api/v1/tasks/not-a-uuid",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Invalid UUID format: 422")
