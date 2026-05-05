"""
API Edge Cases: GET /schedule
=============================
Tests edge cases for getting schedule.

# Depends on: Workflow tests ran first
# Run after: test_07_task_get.py
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestScheduleGetEdgeCases:
    """
    Edge case tests for schedule get endpoint.
    """
    
    def test_schedule_empty_date(self, client, db, log_base_dir, clean_test_data):
        """Test: Schedule for date with no tasks."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        from datetime import date, timedelta
        
        future = (date.today() + timedelta(days=365)).isoformat()
        
        before = tracker.snapshot()
        response = client.get(f"/api/v1/schedule?date={future}")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_12_schedule_get",
            test_name="empty_date",
            step=1,
            endpoint="/api/v1/schedule",
            input_data={"date": future},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("tasks", [])) == 0
        print("Empty date: OK")
    
    def test_schedule_invalid_date_format(self, client, db, log_base_dir, clean_test_data):
        """Test: Schedule with invalid date format."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.get("/api/v1/schedule?date=not-a-date")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_12_schedule_get",
            test_name="invalid_date",
            step=1,
            endpoint="/api/v1/schedule",
            input_data={"date": "not-a-date"},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Invalid date: 422")
    
    def test_schedule_missing_date(self, client, db, log_base_dir, clean_test_data):
        """Test: Schedule without date parameter."""
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        before = tracker.snapshot()
        response = client.get("/api/v1/schedule")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/api",
            test_file="test_12_schedule_get",
            test_name="missing_date",
            step=1,
            endpoint="/api/v1/schedule",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 422
        print("Missing date: 422")
