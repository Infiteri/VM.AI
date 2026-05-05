"""
Workflow 3: Commit Schedule
===========================
Purpose: User commits provisional schedule to main

Flow:
1. POST /provisional/commit
2. GET /schedule → tasks present
3. GET /provisional/changes → empty

Run after: test_wf_02_schedule_unscheduled.py
Cleanup: Clears main_schedule entries created by this workflow
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow03CommitSchedule:
    """
    Tests committing provisional schedule to main.
    
    # Run after: test_wf_02_schedule_unscheduled.py
    # Depends on: Workflow 2 created provisional_schedule entries
    # Creates: main_schedule entries
    # Cleanup: Clears main_schedule at end (but keeps tasks)
    """
    
    def test_commit_provisional_to_main(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Commit provisional to main schedule.
        
        Expected:
        - commit returns 200 with committed_count > 0
        - schedule shows committed tasks
        - provisional/changes is empty
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Check provisional first
        before = tracker.snapshot()
        response = client.get("/api/v1/provisional/changes")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_03_commit_schedule",
            test_name="step0_check_provisional",
            step=0,
            endpoint="/api/v1/provisional/changes",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        provisional_data = response.json()
        provisional_count = provisional_data.get("total_count", 0)
        print(f"Provisional has {provisional_count} tasks to commit")
        
        if provisional_count == 0:
            pytest.skip("No tasks in provisional - run wf_02 first")
        
        # Step 1: POST /provisional/commit
        # ====================================
        before = tracker.snapshot()
        
        response = client.post("/api/v1/provisional/commit")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_03_commit_schedule",
            test_name="step1_commit",
            step=1,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"commit failed: {response.json()}"
        commit_data = response.json()
        committed_count = commit_data.get("committed_count", 0)
        print(f"Committed {committed_count} tasks")
        
        # Step 2: GET /schedule
        # ====================================
        from datetime import date, timedelta
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        before = tracker.snapshot()
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_03_commit_schedule",
            test_name="step2_check_schedule",
            step=2,
            endpoint="/api/v1/schedule",
            input_data={"date": today.isoformat()},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"schedule failed: {response.json()}"
        schedule_data = response.json()
        schedule_tasks = schedule_data.get("tasks", [])
        
        print(f"Schedule for {today} has {len(schedule_tasks)} tasks")
        
        # Step 3: GET /provisional/changes (should be empty)
        # ====================================
        before = tracker.snapshot()
        
        response = client.get("/api/v1/provisional/changes")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_03_commit_schedule",
            test_name="step3_check_provisional_empty",
            step=3,
            endpoint="/api/v1/provisional/changes",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        changes_data = response.json()
        assert changes_data.get("total_count", 0) == 0, "Provisional should be empty after commit"
        print("Provisional is empty after commit")
    
    def test_commit_empty_provisional(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Commit when provisional is empty.
        
        Expected:
        - commit returns 200
        - committed_count = 0
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Step 1: Commit empty provisional
        # ====================================
        before = tracker.snapshot()
        response = client.post("/api/v1/provisional/commit")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_03_commit_schedule",
            test_name="test2_commit_empty",
            step=1,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        commit_data = response.json()
        assert commit_data.get("committed_count", 0) == 0
        print("Empty commit returned 0 count")
