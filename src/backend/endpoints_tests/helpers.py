"""
Test helpers - shared utilities for all API and workflow tests.
"""
import json
import copy
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient


class DBChangeTracker:
    """
    Tracks DB changes by snapshotting tables before/after API calls.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._snapshot = {}
    
    def snapshot(self, tables: list[str] = None) -> dict:
        """
        Capture current state of all tables.
        
        Args:
            tables: List of table names to snapshot. If None, snapshots all tracked tables.
            
        Returns:
            dict: {table_name: [list of row dicts]}
        """
        if tables is None:
            tables = [
                'tasks', 'task_categories', 'task_statistics',
                'category_statistics', 'task_statistics_locations',
                'category_statistics_locations', 'main_schedule',
                'provisional_schedule', 'schedule_changes',
                'unscheduled_tasks', 'task_drafts', 'locations', 'categories'
            ]
        
        snapshot = {}
        
        from app.models import (
            Task, TaskCategory, TaskStatistics, CategoryStatistics,
            TaskStatisticsLocation, CategoryStatisticsLocation,
            MainScheduleSlot, ProvisionalSlot, ScheduleChange,
            UnscheduledTask, TaskDraft, Location, Category
        )
        
        model_map = {
            'tasks': Task,
            'task_categories': TaskCategory,
            'task_statistics': TaskStatistics,
            'category_statistics': CategoryStatistics,
            'task_statistics_locations': TaskStatisticsLocation,
            'category_statistics_locations': CategoryStatisticsLocation,
            'main_schedule': MainScheduleSlot,
            'provisional_schedule': ProvisionalSlot,
            'schedule_changes': ScheduleChange,
            'unscheduled_tasks': UnscheduledTask,
            'task_drafts': TaskDraft,
            'locations': Location,
            'categories': Category,
        }
        
        for table in tables:
            if table not in model_map:
                continue
            
            model = model_map[table]
            rows = self.db.query(model).all()
            
            rows_data = []
            for row in rows:
                row_dict = {}
                for col in model.__table__.columns:
                    val = getattr(row, col.name, None)
                    if isinstance(val, UUID):
                        val = str(val)
                    elif isinstance(val, datetime):
                        val = val.isoformat() if val else None
                    elif hasattr(val, '__dict__'):
                        val = str(val)
                    row_dict[col.name] = val
                rows_data.append(row_dict)
            
            snapshot[table] = rows_data
        
        return snapshot
    
    def compute_changes(self, before: dict, after: dict) -> list:
        """
        Compute changes between two snapshots.
        
        Args:
            before: Snapshot before API call
            after: Snapshot after API call
            
        Returns:
            list: [{table, action, record/old_record/new_record, changes}]
        """
        changes = []
        
        all_tables = set(before.keys()) | set(after.keys())
        
        for table in all_tables:
            before_rows = {str(r.get('id', r.get('task_id', ''))): r for r in before.get(table, [])}
            after_rows = {str(r.get('id', r.get('task_id', ''))): r for r in after.get(table, [])}
            
            before_ids = set(before_rows.keys())
            after_ids = set(after_rows.keys())
            
            deleted_ids = before_ids - after_ids
            for id_ in deleted_ids:
                if id_ and id_ != 'None' and id_ != '':
                    changes.append({
                        'table': table,
                        'action': 'DELETE',
                        'record': before_rows[id_]
                    })
            
            inserted_ids = after_ids - before_ids
            for id_ in inserted_ids:
                if id_ and id_ != 'None' and id_ != '':
                    changes.append({
                        'table': table,
                        'action': 'INSERT',
                        'record': after_rows[id_]
                    })
            
            modified_ids = before_ids & after_ids
            for id_ in modified_ids:
                if id_ and id_ != 'None' and id_ != '':
                    old_record = before_rows[id_]
                    new_record = after_rows[id_]
                    
                    field_changes = {}
                    for key in set(old_record.keys()) | set(new_record.keys()):
                        old_val = old_record.get(key)
                        new_val = new_record.get(key)
                        
                        if old_val != new_val:
                            field_changes[key] = {'old': old_val, 'new': new_val}
                    
                    if field_changes:
                        changes.append({
                            'table': table,
                            'action': 'UPDATE',
                            'record': new_record,
                            'changes': field_changes
                        })
        
        return changes


class TestHelper:
    """
    Shared test utilities for API and workflow tests.
    """
    
    @staticmethod
    def log_result(
        log_dir: str,
        test_file: str,
        test_name: str,
        step: int,
        endpoint: str,
        input_data: dict,
        response,
        db_changes: list,
        result: str = "PASS"
    ):
        """
        Log test result to JSON file.
        
        Args:
            log_dir: Directory for log files
            test_file: Name of test file (without .py)
            test_name: Name of test function
            step: Step number in workflow
            endpoint: API endpoint called
            input_data: Request payload
            response: Response object
            db_changes: List of DB changes
            result: PASS or FAIL
        """
        log_file = Path(log_dir) / f"{test_file}.json"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "test_file": test_file,
            "test_name": test_name,
            "step": step,
            "endpoint": endpoint,
            "input": input_data,
            "response": {
                "status_code": response.status_code,
                "body": response.json() if response.status_code < 400 else None,
                "error": response.json().get('detail') if response.status_code >= 400 else None
            },
            "db_changes": db_changes,
            "result": result
        }
        
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing_logs = json.load(f)
            except json.JSONDecodeError:
                existing_logs = []
        
        existing_logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(existing_logs, f, indent=2)
    
    @staticmethod
    def cleanup_task(db: Session, task_id: UUID):
        """
        Delete a task and all related data (cascade).
        
        Args:
            db: Database session
            task_id: UUID of task to delete
        """
        from app.models import Task
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            db.query(Task).filter(Task.id == task_id).delete()
            db.commit()
    
    @staticmethod
    def cleanup_all_test_data(db: Session, prefix: str = "TEST_"):
        """
        Clean up all test data with given prefix.
        
        Args:
            db: Database session
            prefix: Prefix for test data names
        """
        from app.models import Task, TaskDraft, UnscheduledTask, TaskCategory
        
        db.query(UnscheduledTask).filter(
            UnscheduledTask.task_id.in_(
                db.query(Task.id).filter(Task.name.like(f'{prefix}%'))
            )
        ).delete(synchronize_session=False)
        
        db.query(TaskCategory).filter(
            TaskCategory.task_id.in_(
                db.query(Task.id).filter(Task.name.like(f'{prefix}%'))
            )
        ).delete(synchronize_session=False)
        
        db.query(Task).filter(Task.name.like(f'{prefix}%')).delete(synchronize_session=False)
        db.query(TaskDraft).filter(TaskDraft.name.like(f'{prefix}%')).delete(synchronize_session=False)
        
        db.commit()
    
    @staticmethod
    def create_minimal_task(db: Session, name: str = "Test Task") -> dict:
        """
        Create a minimal task directly in DB (for setup).
        
        Args:
            db: Database session
            name: Task name
            
        Returns:
            dict: {"task_id": UUID, "draft_id": UUID}
        """
        from app.models import Task, TaskDraft, TaskCategory, UnscheduledTask, Location, Category
        from uuid import uuid4
        from datetime import datetime
        
        loc = db.query(Location).first()
        cat = db.query(Category).first()
        
        task_id = uuid4()
        draft_id = uuid4()
        
        task = Task(
            id=task_id,
            name=name,
            difficulty=0.5,
            duration=60,
            importance=0.5,
            fixed_time=False,
            location_id=loc.id if loc else None,
            created_at=datetime.now()
        )
        db.add(task)
        
        draft = TaskDraft(
            id=draft_id,
            name=name,
            difficulty=0.5,
            duration=60,
            importance=0.5,
            fixed_time=False,
            created_at=datetime.now()
        )
        db.add(draft)
        
        if cat:
            tc = TaskCategory(task_id=task_id, category_id=cat.id)
            db.add(tc)
        
        unscheduled = UnscheduledTask(task_id=task_id)
        db.add(unscheduled)
        
        db.commit()
        
        return {"task_id": task_id, "draft_id": draft_id, "task_name": name}
    
    @staticmethod
    def get_task_id_by_name(db: Session, name: str) -> Optional[UUID]:
        """
        Get task ID by name.
        
        Args:
            db: Database session
            name: Task name
            
        Returns:
            UUID or None
        """
        from app.models import Task
        
        task = db.query(Task).filter(Task.name == name).first()
        return task.id if task else None
    
    @staticmethod
    def get_any_scheduled_task(db: Session) -> Optional[UUID]:
        """
        Get ID of any task in main_schedule.
        
        Args:
            db: Database session
            
        Returns:
            UUID or None
        """
        from app.models import MainScheduleSlot
        
        slot = db.query(MainScheduleSlot).first()
        return slot.task_id if slot else None
    
    @staticmethod
    def get_any_unrated_task(db: Session) -> Optional[UUID]:
        """
        Get ID of any unrated task in main_schedule.
        
        Args:
            db: Database session
            
        Returns:
            UUID or None
        """
        from app.models import MainScheduleSlot, Task
        
        slot = db.query(MainScheduleSlot).join(Task).filter(Task.rated == False).first()
        return slot.task_id if slot else None
    
    @staticmethod
    def count_in_table(db: Session, table_name: str) -> int:
        """
        Count rows in a table.
        
        Args:
            db: Database session
            table_name: Name of table
            
        Returns:
            int: Row count
        """
        from sqlalchemy import text
        
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()


class WorkflowContext:
    """
    Stores context data between workflow steps.
    """
    
    def __init__(self):
        self.task_ids = []
        self.draft_ids = []
        self.schedule_slots = []
        self.task_names = []
    
    def add_task(self, task_id: UUID, draft_id: UUID = None, name: str = None):
        self.task_ids.append(task_id)
        if draft_id:
            self.draft_ids.append(draft_id)
        if name:
            self.task_names.append(name)
    
    def get_latest_task_id(self) -> Optional[UUID]:
        return self.task_ids[-1] if self.task_ids else None
    
    def get_latest_draft_id(self) -> Optional[UUID]:
        return self.draft_ids[-1] if self.draft_ids else None
    
    def reset(self):
        self.task_ids = []
        self.draft_ids = []
        self.schedule_slots = []
        self.task_names = []
