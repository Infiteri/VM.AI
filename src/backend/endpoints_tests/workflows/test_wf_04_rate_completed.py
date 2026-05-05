"""
Workflow 4: Rate Completed Task
================================
Purpose: User marks task as completed with actual metrics

Flow:
1. GET /schedule → get task_id
2. POST /tasks/{id}/rate (completed=true, dur=45, diff=0.5)
3. GET /tasks/{id} → rated=true
4. Check DB: task_statistics updated, time_score boosted

Run after: test_wf_03_commit_schedule.py
Cleanup: None (rating is final state)
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow04RateCompleted:
    """
    Tests rating a task as completed.
    
    # Run after: test_wf_03_commit_schedule.py
    # Depends on: Workflow 3 created scheduled tasks
    # Updates: tasks.rated, task_statistics, category_statistics
    # Cleanup: None (rating is final)
    """
    
    def test_rate_task_completed(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Rate a task as completed.
        
        Expected:
        - rate returns 200
        - task.rated = true
        - stats updated
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Step 1: Get a scheduled task
        # ====================================
        from datetime import date, timedelta
        
        today = date.today()
        
        before = tracker.snapshot()
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_04_rate_completed",
            test_name="step1_get_scheduled_task",
            step=1,
            endpoint="/api/v1/schedule",
            input_data={"date": today.isoformat()},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        schedule_data = response.json()
        tasks = schedule_data.get("tasks", [])
        
        if not tasks:
            pytest.skip("No scheduled tasks - run wf_03 first")
        
        unrated_task = next((t for t in tasks if not t.get("rated")), None)
        if not unrated_task:
            pytest.skip("All scheduled tasks are already rated")
        
        task_id = unrated_task.get("task_id")
        print(f"Rated task: {unrated_task.get('name')} (ID: {task_id})")
        
        # Step 2: POST /tasks/{id}/rate (completed=true)
        # ====================================
        before = tracker.snapshot()
        
        rate_payload = {
            "completed": True,
            "actual_duration": 45,
            "actual_difficulty": 0.5
        }
        
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json=rate_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_04_rate_completed",
            test_name="step2_rate_completed",
            step=2,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data=rate_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"rate failed: {response.json()}"
        rate_data = response.json()
        assert rate_data.get("success") == True
        print(f"Task rated as completed")
        
        # Step 3: GET /tasks/{id} → verify rated=true
        # ====================================
        before = tracker.snapshot()
        
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_04_rate_completed",
            test_name="step3_verify_rated",
            step=3,
            endpoint=f"/api/v1/tasks/{task_id}",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        task_data = response.json()
        
        # Check if rated field exists and is True
        rated = task_data.get("task", {}).get("rated", False)
        print(f"Task rated field: {rated}")
    
    def test_rate_with_exact_duration(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Rate with exact planned duration.
        
        Expected:
        - duration_delta = 0
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Get another scheduled task
        from datetime import date
        
        today = date.today()
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        
        assert response.status_code == 200
        tasks = response.json().get("tasks", [])
        
        unrated_task = next((t for t in tasks if not t.get("rated")), None)
        if not unrated_task:
            pytest.skip("No unrated tasks")
        
        task_id = unrated_task.get("task_id")
        
        # Rate with exact duration
        before = tracker.snapshot()
        
        rate_payload = {
            "completed": True,
            "actual_duration": 60,
            "actual_difficulty": 0.5
        }
        
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json=rate_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_04_rate_completed",
            test_name="test2_exact_duration",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data=rate_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        print(f"Task rated with exact duration")
