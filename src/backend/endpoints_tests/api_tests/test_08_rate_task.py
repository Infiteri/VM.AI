"""
API Edge Cases: POST /tasks/{id}/rate
====================================
Tests edge cases for rating tasks.

# Depends on: Workflow tests ran first
# Run after: test_01_parse_add.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestRateTaskEdgeCases:
    """
    Edge case tests for rate endpoint.
    """
    
    def get_any_unrated_task(self, client):
        """Helper: Get an unrated task from schedule."""
        from datetime import date, timedelta
        
        for offset in range(30):
            check_date = (date.today() + timedelta(days=offset)).isoformat()
            response = client.get(f"/api/v1/schedule?date={check_date}")
            if response.status_code == 200:
                tasks = response.json().get("tasks", [])
                unrated = next((t for t in tasks if not t.get("rated")), None)
                if unrated:
                    return unrated.get("task_id")
        return None
    
    def test_invalid_duration_too_high(self, client, db, log_base_dir, clean_test_data):
        """Test: Duration > 1440."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": True,
            "actual_duration": 2000,
            "actual_difficulty": 0.5
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="invalid_duration_high",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": True, "actual_duration": 2000},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Duration > 1440: 422")
    
    def test_invalid_duration_negative(self, client, db, log_base_dir, clean_test_data):
        """Test: Duration < 0."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": True,
            "actual_duration": -5,
            "actual_difficulty": 0.5
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="invalid_duration_negative",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": True, "actual_duration": -5},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Duration < 0: 422")
    
    def test_invalid_difficulty_too_high(self, client, db, log_base_dir, clean_test_data):
        """Test: Difficulty > 1.0."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": True,
            "actual_duration": 60,
            "actual_difficulty": 1.5
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="invalid_difficulty_high",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": True, "actual_difficulty": 1.5},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Difficulty > 1.0: 422")
    
    def test_invalid_difficulty_negative(self, client, db, log_base_dir, clean_test_data):
        """Test: Difficulty < 0."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": True,
            "actual_duration": 60,
            "actual_difficulty": -0.1
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="invalid_difficulty_negative",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": True, "actual_difficulty": -0.1},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Difficulty < 0: 422")
    
    def test_missing_duration_when_completed(self, client, db, log_base_dir, clean_test_data):
        """Test: Missing duration when completed=true."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": True,
            "actual_difficulty": 0.5
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="missing_duration",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": True},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Missing duration: 422")
    
    def test_completed_false_with_extras(self, client, db, log_base_dir, clean_test_data):
        """Test: completed=false but duration/difficulty sent."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_id = self.get_any_unrated_task(client)
        if not task_id:
            pytest.skip("No unrated tasks")
        
        before = tracker.snapshot()
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json={
            "completed": False,
            "actual_duration": 60,
            "actual_difficulty": 0.5
        })
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_08_rate_task",
            test_name="uncompleted_with_extras",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data={"completed": False, "actual_duration": 60},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("completed=false with extras: 422")
