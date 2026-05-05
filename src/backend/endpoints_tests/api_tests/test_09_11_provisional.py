"""
API Edge Cases: POST /provisional/commit and /reset
===================================================
Tests edge cases for provisional endpoints.

# Depends on: Workflow tests ran first
# Run after: test_04_task_create.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestProvisionalEdgeCases:
    """
    Edge case tests for provisional endpoints.
    """
    
    def test_commit_empty(self, client, db, log_base_dir, clean_test_data):
        """Test: Commit when no changes."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit to clear provisional
        client.post("/api/v1/provisional/commit")
        
        before = tracker.snapshot()
        response = client.post("/api/v1/provisional/commit")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_11_provisional_commit",
            test_name="commit_empty",
            step=1,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("committed_count", 0) == 0
        print("Empty commit: OK")
    
    def test_changes_empty(self, client, db, log_base_dir, clean_test_data):
        """Test: Changes when empty."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit to clear
        client.post("/api/v1/provisional/commit")
        
        before = tracker.snapshot()
        response = client.get("/api/v1/provisional/changes")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_09_provisional_changes",
            test_name="changes_empty",
            step=1,
            endpoint="/api/v1/provisional/changes",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("total_count", 0) == 0
        print("Empty changes: OK")
    
    def test_reset_empty(self, client, db, log_base_dir, clean_test_data):
        """Test: Reset when empty."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit to clear
        client.post("/api/v1/provisional/commit")
        
        before = tracker.snapshot()
        response = client.post("/api/v1/provisional/reset")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_10_provisional_reset",
            test_name="reset_empty",
            step=1,
            endpoint="/api/v1/provisional/reset",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("changes_discarded", 0) == 0
        print("Empty reset: OK")
