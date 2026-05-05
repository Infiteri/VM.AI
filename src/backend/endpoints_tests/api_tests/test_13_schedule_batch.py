"""
API Edge Cases: POST /schedule/batch
=====================================
Tests edge cases for batch scheduling endpoint.

# Depends on: Workflow tests ran first
# Run after: test_02_parse_modify.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestBatchEdgeCases:
    """
    Edge case tests for batch scheduling endpoint.
    """
    
    def test_batch_empty_queue(self, client, db, log_base_dir, clean_test_data):
        """Test: Batch with empty queue."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit to clear unscheduled
        client.post("/api/v1/provisional/commit")
        
        before = tracker.snapshot()
        response = client.post("/api/v1/schedule/batch")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_13_schedule_batch",
            test_name="empty_queue",
            step=1,
            endpoint="/api/v1/schedule/batch",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("scheduled_count", 0) == 0
        print("Empty queue batch: OK")
    
    def test_batch_returns_results(self, client, db, log_base_dir, clean_test_data):
        """Test: Batch returns proper results structure."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Create a task first
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": "TEST_BATCH_WORKFLOW"})
        if parse_resp.status_code == 200:
            task_data = parse_resp.json().get("task", {})
            client.post("/api/v1/tasks/", json={
                "task": task_data,
                "draft_id": parse_resp.json().get("draft_id")
            })
        
        before = tracker.snapshot()
        response = client.post("/api/v1/schedule/batch")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_13_schedule_batch",
            test_name="returns_results",
            step=1,
            endpoint="/api/v1/schedule/batch",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields
        assert "scheduled_count" in data
        assert "failed_count" in data
        assert "results" in data
        assert "execution_time_ms" in data
        print("Results structure: OK")
