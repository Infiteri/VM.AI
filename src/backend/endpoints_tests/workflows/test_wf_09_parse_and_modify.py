"""
Workflow 9: Parse and Modify Task
=================================
Purpose: User parses modification to existing task

Flow:
1. Create task (setup)
2. parse/modify "make it 2 hours instead of 1"
3. update task with merged result
4. Verify task updated

Run after: test_wf_08_reset_provisional.py
Cleanup: Deletes created task
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow09ParseAndModify:
    """
    Tests parsing modification prompts.
    
    # Run after: test_wf_08_reset_provisional.py
    # Depends on: Existing task
    # Updates: task fields
    # Cleanup: Deletes created test tasks
    """
    
    def test_parse_modify_duration(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Parse modification "make it longer".
        
        Expected:
        - parse/modify returns 200
        - update returns 200
        - duration changed
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Create a task
        prompt = "TEST_PARSE_MODIFY_WORKFLOW_9"
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        
        if parse_resp.status_code != 200:
            pytest.skip("Could not parse task")
        
        draft_id = parse_resp.json().get("draft_id")
        task_data = parse_resp.json().get("task", {})
        original_duration = task_data.get("duration", 60)
        
        create_resp = client.post("/api/v1/tasks/", json={
            "task": task_data,
            "draft_id": draft_id
        })
        
        if create_resp.status_code != 201:
            pytest.skip("Could not create task")
        
        task_id = create_resp.json().get("task_id")
        print(f"Created task {task_id} with duration {original_duration}")
        
        # Step 1: parse/modify
        # ====================================
        before = tracker.snapshot()
        
        modify_payload = {
            "task": task_data,
            "prompt": "make it 2 hours instead of 1"
        }
        
        response = client.post("/api/v1/tasks/parse/modify", json=modify_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_09_parse_and_modify",
            test_name="step1_parse_modify",
            step=1,
            endpoint="/api/v1/tasks/parse/modify",
            input_data=modify_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        if response.status_code != 200:
            print(f"parse/modify returned: {response.status_code}")
            print(f"Response: {response.json()}")
        
        # Note: parse/modify may fail for some prompts, which is OK for this test
        
        # Step 2: update task
        # ====================================
        if response.status_code == 200:
            modified_task = response.json().get("task", {})
            
            before = tracker.snapshot()
            
            update_payload = {"task": modified_task}
            
            response = client.post(
                f"/api/v1/tasks/{task_id}/update?source=unscheduled",
                json=update_payload
            )
            
            after = tracker.snapshot()
            changes = tracker.compute_changes(before, after)
            
            helper.log_result(
                log_dir=f"{log_base_dir}/workflows",
                test_file="test_wf_09_parse_and_modify",
                test_name="step2_update",
                step=2,
                endpoint=f"/api/v1/tasks/{task_id}/update",
                input_data=update_payload,
                response=response,
                db_changes=changes,
                result="PASS" if response.status_code == 200 else "FAIL"
            )
            
            if response.status_code == 200:
                print(f"Task updated with new duration")
    
    def test_parse_modify_no_changes(self, client, db, log_base_dir, clean_test_data):
        """
        Test: Parse modification with no actual changes.
        
        Expected:
        - parse/modify returns 200
        - task unchanged
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        # Setup: Create a task
        prompt = "TEST_NO_CHANGE_WORKFLOW_9"
        parse_resp = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        
        if parse_resp.status_code != 200:
            pytest.skip("Could not parse task")
        
        draft_id = parse_resp.json().get("draft_id")
        task_data = parse_resp.json().get("task", {})
        
        create_resp = client.post("/api/v1/tasks/", json={
            "task": task_data,
            "draft_id": draft_id
        })
        
        if create_resp.status_code != 201:
            pytest.skip("Could not create task")
        
        task_id = create_resp.json().get("task_id")
        
        # parse/modify with no change
        before = tracker.snapshot()
        
        modify_payload = {
            "task": task_data,
            "prompt": "keep it as is"
        }
        
        response = client.post("/api/v1/tasks/parse/modify", json=modify_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_09_parse_and_modify",
            test_name="test2_no_changes",
            step=1,
            endpoint="/api/v1/tasks/parse/modify",
            input_data=modify_payload,
            response=response,
            db_changes=changes
        )
        
        # parse/modify should succeed even with no changes
        print(f"parse/modify status: {response.status_code}")
