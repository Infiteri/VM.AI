"""
Workflow 2: Schedule Unsaturated Tasks
=======================================
Purpose: User schedules unscheduled tasks

Flow:
1. Ensure unscheduled queue has tasks (from Workflow 1)
2. POST /schedule/batch
3. GET /provisional/changes → tasks scheduled

Run after: test_wf_01_add_task_to_queue.py
Cleanup: Resets provisional schedule, deletes test tasks
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow02ScheduleUnsaturated:
    """
    Tests scheduling unscheduled tasks to provisional.
    
    # Run after: test_wf_01_add_task_to_queue.py
    # Depends on: Workflow 1 created tasks in unscheduled queue
    # Creates: provisional_schedule entries
    # Cleanup: Deletes test tasks at end
    """
    
    def test_schedule_unscheduled_tasks(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Schedule all unscheduled tasks.
        
        Expected:
        - batch returns 200 with scheduled_count > 0
        - provisional/changes shows scheduled tasks
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Check unscheduled count first
        before = tracker.snapshot()
        response = client.get("/api/v1/tasks/unscheduled")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_02_schedule_unscheduled",
            test_name="step0_check_queue",
            step=0,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        unscheduled = response.json()
        queue_count = unscheduled.get("total_count", 0)
        print(f"Unscheduled queue has {queue_count} tasks")
        
        if queue_count == 0:
            pytest.skip("No tasks in unscheduled queue - run wf_01 first")
        
        # Step 1: POST /schedule/batch
        # ====================================
        before = tracker.snapshot()
        
        response = client.post("/api/v1/schedule/batch")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_02_schedule_unscheduled",
            test_name="step1_batch_schedule",
            step=1,
            endpoint="/api/v1/schedule/batch",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"batch failed: {response.json()}"
        batch_data = response.json()
        
        scheduled_count = batch_data.get("scheduled_count", 0)
        print(f"Scheduled {scheduled_count} tasks")
        
        # Step 2: Check provisional/changes
        # ====================================
        before = tracker.snapshot()
        
        response = client.get("/api/v1/provisional/changes")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_02_schedule_unscheduled",
            test_name="step2_check_provisional",
            step=2,
            endpoint="/api/v1/provisional/changes",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"provisional/changes failed: {response.json()}"
        provisional_data = response.json()
        changes_count = provisional_data.get("total_count", 0)
        
        print(f"Provisional has {changes_count} scheduled tasks")
        assert changes_count > 0, "No tasks in provisional"
    
    def test_batch_with_empty_queue(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Batch with empty queue returns success with 0 scheduled.
        
        Expected:
        - batch returns 200
        - scheduled_count = 0
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Step 1: Commit current provisional to clear unscheduled
        # ====================================
        before = tracker.snapshot()
        response = client.post("/api/v1/provisional/commit")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_02_schedule_unscheduled",
            test_name="test2_commit_first",
            step=1,
            endpoint="/api/v1/provisional/commit",
            input_data={},
            response=response,
            db_changes=changes
        )
        
        # Step 2: Try batch with empty queue
        # ====================================
        before = tracker.snapshot()
        response = client.post("/api/v1/schedule/batch")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_02_schedule_unscheduled",
            test_name="test2_batch_empty",
            step=2,
            endpoint="/api/v1/schedule/batch",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        batch_data = response.json()
        assert batch_data.get("scheduled_count", 0) == 0
        print("Empty queue batch returns 0 scheduled")
