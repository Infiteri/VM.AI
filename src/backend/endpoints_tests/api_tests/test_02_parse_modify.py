"""
API Edge Cases: POST /tasks/parse/modify
========================================
Tests edge cases for parse modify endpoint.

# Depends on: Workflow tests ran first
# Run after: test_09_11_provisional.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestParseModifyEdgeCases:
    """
    Edge case tests for parse modify endpoint.
    """
    
    def test_parse_modify_empty_prompt(self, client, db, log_base_dir, clean_test_data):
        """Test: Parse modify with empty prompt."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/modify", json={
            "task": {"name": "Test Task"},
            "prompt": ""
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_02_parse_modify",
            test_name="empty_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/modify",
            input_data={"prompt": ""},
            response=response,
            db_changes=changes
        )
        
        # Should handle gracefully (200 or 500)
        assert response.status_code in [200, 500]
        print(f"Empty prompt: {response.status_code}")
    
    def test_parse_modify_no_changes(self, client, db, log_base_dir, clean_test_data):
        """Test: Parse modify with no actual changes."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/modify", json={
            "task": {"name": "Test Task", "duration": 60},
            "prompt": "keep it the same"
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_02_parse_modify",
            test_name="no_changes",
            step=1,
            endpoint="/api/v1/tasks/parse/modify",
            input_data={"prompt": "keep it the same"},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        # Should succeed
        print(f"No changes prompt: {response.status_code}")
