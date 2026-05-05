"""
API Edge Cases: GET /tasks/unscheduled
======================================
Tests edge cases for unscheduled queue.

# Depends on: Workflow tests ran first
# Run after: test_06_task_delete.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestUnscheduledEdgeCases:
    """
    Edge case tests for unscheduled endpoint.
    """
    
    def test_unscheduled_empty(self, client, db, log_base_dir, clean_test_data):
        """Test: Empty unscheduled queue."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit everything to clear unscheduled
        client.post("/api/v1/provisional/commit")
        
        before = tracker.snapshot()
        response = client.get("/api/v1/tasks/unscheduled")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_03_unscheduled",
            test_name="empty_queue",
            step=1,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("total_count", 0) == 0
        print("Empty queue: OK")
    
    def test_unscheduled_with_limit(self, client, db, log_base_dir, clean_test_data):
        """Test: Unscheduled with limit parameter."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.get("/api/v1/tasks/unscheduled?limit=5")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_03_unscheduled",
            test_name="with_limit",
            step=1,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={"limit": 5},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        tasks = data.get("tasks", [])
        assert len(tasks) <= 5
        print(f"With limit=5: {len(tasks)} tasks returned")
    
    def test_unscheduled_limit_zero(self, client, db, log_base_dir, clean_test_data):
        """Test: Unscheduled with limit=0."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.get("/api/v1/tasks/unscheduled?limit=0")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_03_unscheduled",
            test_name="limit_zero",
            step=1,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={"limit": 0},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        print("Limit=0: OK")
