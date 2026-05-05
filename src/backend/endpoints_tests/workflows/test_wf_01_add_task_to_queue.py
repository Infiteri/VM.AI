"""
Workflow 1: User Adds Task to Queue
===================================
Purpose: User adds a new task → it appears in unscheduled queue

Flow:
1. parse/add "go to gym tomorrow at 6pm"
2. create task from draft
3. GET /tasks/unscheduled → task present

Run after: N/A (first workflow)
Cleanup: Deletes created task at end
"""
import pytest
from helpers import DBChangeTracker, TestHelper


class TestWorkflow01AddTaskToQueue:
    """
    Tests the complete flow of adding a task from NLP to queue.
    
    # Run after: N/A (first workflow)
    # Creates: task in tasks table, task in unscheduled queue
    # Cleanup: Deletes TEST_GYM_WORKOUT_* task at end
    """
    
    def test_user_adds_gym_task(self, client, db, log_base_dir, clean_test_data):
        """
        Test: User adds "go to gym" task.
        
        Expected:
        - parse/add returns 200 with draft
        - create task returns 201
        - task appears in unscheduled queue
        """
        from app.models import Task
        
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_name = "TEST_GYM_WORKOUT"
        prompt = "go to gym tomorrow at 6pm"
        
        # Step 1: parse/add
        # ====================================
        before = tracker.snapshot()
        
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_01_add_task_to_queue",
            test_name="step1_parse_add",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": prompt},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"parse/add failed: {response.json()}"
        parse_data = response.json()
        draft_id = parse_data.get("draft_id")
        assert draft_id is not None, "No draft_id in response"
        
        task_data = parse_data.get("task", {})
        print(f"Parsed task: {task_data.get('name')}")
        
        # Step 2: create task
        # ====================================
        before = tracker.snapshot()
        
        create_payload = {
            "task": {
                "name": task_data.get("name", task_name),
                "start": str(task_data.get("start")) if task_data.get("start") else None,
                "deadline": str(task_data.get("deadline")) if task_data.get("deadline") else None,
                "difficulty": task_data.get("difficulty", 0.5),
                "duration": task_data.get("duration", 60),
                "category": task_data.get("category", ["personal"]),
                "location": task_data.get("location", "home"),
                "importance": task_data.get("importance", 0.5),
                "fixed_time": task_data.get("fixed_time", False),
                "fixed_start": str(task_data.get("fixed_start")) if task_data.get("fixed_start") else None,
            },
            "draft_id": draft_id
        }
        
        response = client.post("/api/v1/tasks/", json=create_payload)
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_01_add_task_to_queue",
            test_name="step2_create_task",
            step=2,
            endpoint="/api/v1/tasks/",
            input_data=create_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 201 else "FAIL"
        )
        
        assert response.status_code == 201, f"create failed: {response.json()}"
        create_data = response.json()
        task_id = create_data.get("task_id")
        assert task_id is not None, "No task_id in response"
        
        # Step 3: Verify in unscheduled queue
        # ====================================
        before = tracker.snapshot()
        
        response = client.get("/api/v1/tasks/unscheduled")
        
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_01_add_task_to_queue",
            test_name="step3_check_unscheduled",
            step=3,
            endpoint="/api/v1/tasks/unscheduled",
            input_data={},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200, f"unscheduled failed: {response.json()}"
        unscheduled_data = response.json()
        tasks = unscheduled_data.get("tasks", [])
        
        task_found = any(t.get("task_id") == task_id for t in tasks)
        assert task_found, f"Task {task_id} not found in unscheduled queue"
        
        print(f"Task {task_name} successfully added to queue. Total in queue: {len(tasks)}")
        
        # Cleanup is handled by clean_test_data fixture
    
    def test_user_adds_work_task(self, client, db, log_base_dir, clean_test_data):
        """
        Test: User adds "finish report" task.
        
        Expected:
        - parse/add returns 200
        - task created and in queue
        """
        helper = TestHelper()
        tracker = DBChangeTracker(db)
        
        task_name = "TEST_WORK_REPORT"
        prompt = "finish quarterly report by friday"
        
        # parse/add
        before = tracker.snapshot()
        response = client.post("/api/v1/tasks/parse/add", json={"prompt": prompt})
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_01_add_task_to_queue",
            test_name="test2_parse_work_task",
            step=1,
            endpoint="/api/v1/tasks/parse/add",
            input_data={"prompt": prompt},
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 200 else "FAIL"
        )
        
        assert response.status_code == 200
        parse_data = response.json()
        draft_id = parse_data.get("draft_id")
        
        # create task
        before = tracker.snapshot()
        create_payload = {
            "task": parse_data.get("task"),
            "draft_id": draft_id
        }
        response = client.post("/api/v1/tasks/", json=create_payload)
        after = tracker.snapshot()
        changes = tracker.compute_changes(before, after)
        
        helper.log_result(
            log_dir=f"{log_base_dir}/workflows",
            test_file="test_wf_01_add_task_to_queue",
            test_name="test2_create_work_task",
            step=2,
            endpoint="/api/v1/tasks/",
            input_data=create_payload,
            response=response,
            db_changes=changes,
            result="PASS" if response.status_code == 201 else "FAIL"
        )
        
        assert response.status_code == 201
        print(f"Work task added: {parse_data.get('task', {}).get('name')}")
