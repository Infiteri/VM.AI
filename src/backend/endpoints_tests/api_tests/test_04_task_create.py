"""
API Edge Cases: POST /tasks
===========================
Tests edge cases for creating tasks.

# Depends on: Workflow tests ran first
# Run after: test_12_schedule_get.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestTaskCreateEdgeCases:
    """
    Edge case tests for task create endpoint.
    """
    
    def test_create_missing_name(self, client, db, log_base_dir, clean_test_data):
        """Test: Create task without name."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/", json={
            "task": {
                "difficulty": 0.5,
                "duration": 60
            }
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_04_task_create",
            test_name="missing_name",
            step=1,
            endpoint="/api/v1/tasks/",
            input_data={"task": {"difficulty": 0.5}},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Missing name: 422")
    
    def test_create_invalid_difficulty(self, client, db, log_base_dir, clean_test_data):
        """Test: Create task with invalid difficulty."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/", json={
            "task": {
                "name": "Test Task",
                "difficulty": 1.5,
                "duration": 60
            }
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_04_task_create",
            test_name="invalid_difficulty",
            step=1,
            endpoint="/api/v1/tasks/",
            input_data={"task": {"name": "Test", "difficulty": 1.5}},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Invalid difficulty: 422")
    
    def test_create_negative_duration(self, client, db, log_base_dir, clean_test_data):
        """Test: Create task with negative duration."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/", json={
            "task": {
                "name": "Test Task",
                "difficulty": 0.5,
                "duration": -10
            }
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_04_task_create",
            test_name="negative_duration",
            step=1,
            endpoint="/api/v1/tasks/",
            input_data={"task": {"name": "Test", "duration": -10}},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Negative duration: 422")
