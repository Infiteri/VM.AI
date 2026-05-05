"""
API Edge Cases: POST /tasks/parse/add
======================================
Tests edge cases not covered in workflows.

# Depends on: Workflow tests ran first
# Run after: test_wf_10_full_lifecycle.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestParseAddEdgeCases:
    """
    Edge case tests for parse/add endpoint.
    """
    
    def test_empty_prompt(self, client, db, log_base_dir, clean_test_data):
        """Test: Empty prompt string."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": ""})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="empty_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": ""},
            response=response,
            db_changes=changes
        )
        
        # Should return 500 or 422, not crash
        assert response.status_code in [400, 422, 500]
        print(f"Empty prompt: {response.status_code}")
    
    def test_very_long_prompt(self, client, db, log_base_dir, clean_test_data):
        """Test: Very long prompt."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        long_prompt = "go to the gym at 6pm and do a full workout routine " * 10
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": long_prompt})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="long_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": "very long..."},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 413, 422]
        print(f"Long prompt: {response.status_code}")
    
    def test_no_prompt_field(self, client, db, log_base_dir, clean_test_data):
        """Test: Missing prompt field."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="missing_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Missing prompt: 422")
    
    def test_numeric_prompt(self, client, db, log_base_dir, clean_test_data):
        """Test: Numeric-only prompt."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": "12345"})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="numeric_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": "12345"},
            response=response,
            db_changes=changes
        )
        
        # Should handle gracefully
        print(f"Numeric prompt: {response.status_code}")
    
    def test_special_characters(self, client, db, log_base_dir, clean_test_data):
        """Test: Special characters in prompt."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": "task @#$%^&*()"})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="special_chars",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": "task @#$%"},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        print("Special chars: OK")
    
    def test_unicode_prompt(self, client, db, log_base_dir, clean_test_data):
        """Test: Unicode in prompt."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": "совещание в 3 часа"})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_01_parse_add",
            test_name="unicode_prompt",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": "совещание..."},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        print("Unicode: OK")
