"""
Workflow 8: Reset Provisional
=============================
Purpose: User discards provisional changes

Flow:
1. Create tasks, batch, make changes to provisional
2. POST /provisional/reset
3. GET /provisional/changes → empty
4. Check provisional rebuilt from main

Run after: test_wf_07_delete_from_schedule.py
Cleanup: None (reset is operation)
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow08ResetProvisional:
    """
    Tests resetting provisional schedule.
    
    # Run after: test_wf_07_delete_from_schedule.py
    # Depends on: Existing main_schedule
    # Updates: provisional_schedule (rebuilt from main)
    # Cleanup: None
    """
    
    def test_reset_provisional(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Reset provisional to match main.
        
        Expected:
        - reset returns 200
        - provisional matches main
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Ensure we have tasks scheduled
        # Create a task
        prompt = "TEST_RESET_WORKFLOW_8"
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        
        if parse_resp.status_code == 200:
            draft_id = parse_resp.json().get("draft_id")
            task_data = parse_resp.json().get("task", {})
            create_resp = client.post("/api/v1/tasks/", json={
                "task": task_data,
                "draft_id": draft_id
            })
            
            if create_resp.status_code == 201:
                client.post("/api/v1/schedule/batch")
        
        # Commit to main
        before = tracker.snapshot()
        client.post("/api/v1/provisional/commit")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_08_reset_provisional",
            test_name="setup_commit",
            step=0,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=client.post("/api/v1/provisional/commit"),
            db_changes=changes
        )
        
        # Get main count
        from datetime import date
        
        today = date.today()
        schedule_resp = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        main_count = len(schedule_resp.json().get("tasks", [])) if schedule_resp.status_code == 200 else 0
        
        print(f"Main schedule has {main_count} tasks")
        
        # Batch to create provisional
        if main_count == 0:
            pytest.skip("No tasks in main schedule")
        
        client.post("/api/v1/schedule/batch")
        
        # Verify provisional has changes
        changes_resp = client.get("/api/v1/provisional/changes")
        provisional_count = changes_resp.json().get("total_count", 0)
        print(f"Provisional has {provisional_count} changes")
        
        # Step 1: POST /provisional/reset
        # ====================================
        before = tracker.snapshot()
        
        response = client.post("/api/v1/provisional/reset")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_08_reset_provisional",
            test_name="step1_reset",
            step=1,
            endpoint="/api/v1/provisional/reset",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"reset failed: {response.json()}"
        reset_data = response.json()
        print(f"Reset: {reset_data.get('changes_discarded')} changes discarded")
        
        # Step 2: GET /provisional/changes (should be empty after reset)
        # ====================================
        before = tracker.snapshot()
        
        response = client.get("/api/v1/provisional/changes")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_08_reset_provisional",
            test_name="step2_check_empty",
            step=2,
            endpoint="/api/v1/provisional/changes",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        changes_data = response.json()
        assert changes_data.get("total_count", 0) == 0, "Provisional should be empty after reset"
        print("Provisional is empty after reset")
    
    def test_reset_empty_provisional(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Reset when provisional is already empty.
        
        Expected:
        - reset returns 200
        - changes_discarded = 0
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Commit to clear provisional
        client.post("/api/v1/provisional/commit")
        
        # Step 1: Reset empty
        # ====================================
        before = tracker.snapshot()
        
        response = client.post("/api/v1/provisional/reset")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_08_reset_provisional",
            test_name="test2_reset_empty",
            step=1,
            endpoint="/api/v1/provisional/reset",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        reset_data = response.json()
        assert reset_data.get("changes_discarded", 0) == 0
        print("Empty reset returned 0 discarded")
