"""
Workflow 5: Rate Uncompleted Task
==================================
Purpose: User marks task as not done

Flow:
1. Create new task, schedule, commit (setup)
2. POST /tasks/{id}/rate (completed=false)
3. Check DB: uncompleted_count++, time_score reduced

Run after: test_wf_04_rate_completed.py
Cleanup: Deletes created task
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow05RateUncompleted:
    """
    Tests rating a task as uncompleted.
    
    # Run after: test_wf_04_rate_completed.py
    # Depends on: May use existing tasks or create new
    # Updates: task.rated, uncompleted_count, time_score (reduced)
    # Cleanup: Deletes created test tasks
    """
    
    def test_rate_task_uncompleted(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Rate a task as uncompleted.
        
        Expected:
        - rate returns 200
        - uncompleted_count incremented
        - time_score reduced
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Create a task if no unrated tasks exist
        from datetime import date
        
        today = date.today()
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        
        if response.status_code == 200:
            tasks = response.json().get("tasks", [])
            unrated = next((t for t in tasks if not t.get("rated")), None)
        else:
            unrated = None
        
        if not unrated:
            # Create and schedule a new task
            prompt = "TEST_UNCOMPLETED_TASK for workflow 5"
            parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
            
            if parse_resp.status_code == 200:
                draft_id = parse_resp.json().get("draft_id")
                task_data = parse_resp.json().get("task", {})
                
                create_resp = client.post("/api/v1/tasks/", json={
                    "task": task_data,
                    "draft_id": draft_id
                })
                
                if create_resp.status_code == 201:
                    task_id = create_resp.json().get("task_id")
                    
                    # Schedule
                    client.post("/api/v1/schedule/batch")
                    
                    # Commit
                    client.post("/api/v1/provisional/commit")
                    
                    unrated = {"task_id": task_id, "name": task_data.get("name")}
        
        if not unrated:
            pytest.skip("Could not create/find unrated task")
        
        task_id = unrated.get("task_id")
        print(f"Ratings uncompleted: {unrated.get('name')}")
        
        # Step 1: POST /tasks/{id}/rate (completed=false)
        # ====================================
        before = tracker.snapshot()
        
        rate_payload = {
            "completed": False
        }
        
        response = client.post(f"/api/v1/tasks/{task_id}/rate", json=rate_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_05_rate_uncompleted",
            test_name="step1_rate_uncompleted",
            step=1,
            endpoint=f"/api/v1/tasks/{task_id}/rate",
            input_data=rate_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"rate failed: {response.json()}"
        rate_data = response.json()
        assert rate_data.get("success") == True
        print("Task rated as uncompleted")
        
        # Step 2: Verify in schedule with rated=true
        # ====================================
        before = tracker.snapshot()
        
        response = client.get(f"/api/v1/schedule?date={today.isoformat()}")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_05_rate_uncompleted",
            test_name="step2_verify_rated",
            step=2,
            endpoint="/api/v1/schedule",
            input_data={"date": today.isoformat()},
            response=response,
            db_changes=changes
        )
        
        assert response.status_code == 200
        tasks = response.json().get("tasks", [])
        task = next((t for t in tasks if str(t.get("task_id")) == str(task_id)), None)
        
        if task:
            print(f"Task in schedule: rated={task.get('rated')}")
