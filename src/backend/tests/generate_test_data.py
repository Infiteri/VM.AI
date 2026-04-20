"""
Test Data Generator for Enrichment Testing

Generates test data with various scenarios for testing enrichment:
- Cold start (empty stats)
- Partial data (some buckets missing)
- Full data (all buckets, records >= 3)

Run from backend directory:
    cd src/backend
    python tests/generate_test_data.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from uuid import UUID, uuid4
from app.core.database import SessionLocal
from app.models.category import Category
from app.models.location import Location
from app.models.draft import TaskDraft
from app.models.statistics import (
    TaskStatistics,
    CategoryStatistics,
    TaskStatisticsLocation,
    CategoryStatisticsLocation,
)
from app.services.task_matcher import TaskMatcher


def clear_all_data():
    """Delete all records from test tables (in correct order for FK constraints)."""
    db = SessionLocal()

    try:
        print("Clearing existing test data...")

        db.query(TaskStatisticsLocation).delete()
        db.query(CategoryStatisticsLocation).delete()
        db.query(TaskStatistics).delete()
        db.query(CategoryStatistics).delete()
        db.query(TaskDraft).delete()
        db.query(Location).delete()
        db.query(Category).delete()

        db.commit()
        print("   Cleared all data from 7 tables")

    except Exception as e:
        print(f"ERROR clearing data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def generate_test_data():
    db = SessionLocal()

    try:
        clear_all_data()

        print("=" * 60)
        print("Generating Test Data for Enrichment Testing")
        print("=" * 60)

        # ============================================================
        # 1. CATEGORIES (10 records)
        # ============================================================
        print("\n[1/7] Creating categories...")
        category_names = [
            "study",
            "fitness",
            "work",
            "personal",
            "reading",
            "coding",
            "shopping",
            "cooking",
            "gaming",
            "music",
        ]

        categories = []
        for name in category_names:
            cat = Category(name=name)
            db.add(cat)
            categories.append(cat)

        db.flush()
        print(f"   Created {len(categories)} categories")

        # ============================================================
        # 2. LOCATIONS (10 records)
        # ============================================================
        print("\n[2/7] Creating locations...")
        location_names = [
            "home",
            "library",
            "office",
            "gym",
            "coffee_shop",
            "park",
            "university",
            "bookstore",
            "kitchen",
            "bedroom",
        ]

        locations = []
        for name in location_names:
            loc = Location(name=name)
            db.add(loc)
            locations.append(loc)

        db.flush()
        print(f"   Created {len(locations)} locations")

        # ============================================================
        # 3. TASKS_STATISTICS (10 records with variations)
        # ============================================================
        print("\n[3/7] Creating tasks_statistics...")

        task_stats_records = [
            # Full data: records >= 3, all 3 buckets filled
            {
                "task_name": "chemistry homework",
                "avg_duration": {
                    "0.0": {"count": 5, "avg": 30},
                    "0.5": {"count": 3, "avg": 45},
                    "1.0": {"count": 4, "avg": 60},
                },
                "avg_duration_delta": {
                    "0.5": {"count": 3, "avg": 10},
                    "1.0": {"count": 2, "avg": 15},
                },
                "avg_difficulty": 0.65,
                "avg_difficulty_delta": 0.1,
                "completed_count": 8,
                "uncompleted_count": 2,
                "records": 10,
                "task_time_scores": {"09:00": 2.5, "10:00": 1.8, "14:00": 2.0},
            },
            {
                "task_name": "math assignment",
                "avg_duration": {
                    "0.0": {"count": 3, "avg": 25},
                    "0.5": {"count": 4, "avg": 40},
                    "1.0": {"count": 3, "avg": 55},
                },
                "avg_duration_delta": {"0.5": {"count": 2, "avg": 8}},
                "avg_difficulty": 0.55,
                "avg_difficulty_delta": 0.05,
                "completed_count": 6,
                "uncompleted_count": 1,
                "records": 7,
                "task_time_scores": {"09:00": 2.0, "15:00": 1.5},
            },
            {
                "task_name": "physics lab",
                "avg_duration": {
                    "0.5": {"count": 5, "avg": 50},
                    "1.0": {"count": 2, "avg": 70},
                },
                "avg_duration_delta": {"0.5": {"count": 3, "avg": 12}},
                "avg_difficulty": 0.75,
                "avg_difficulty_delta": 0.15,
                "completed_count": 5,
                "uncompleted_count": 0,
                "records": 5,
                "task_time_scores": {"11:00": 1.8},
            },
            # Partial: records >= 3, but only 1-2 buckets
            {
                "task_name": "biology report",
                "avg_duration": {"0.5": {"count": 2, "avg": 35}},
                "avg_difficulty": 0.5,
                "completed_count": 3,
                "uncompleted_count": 1,
                "records": 4,
            },
            {
                "task_name": "history essay",
                "avg_duration": {"1.0": {"count": 3, "avg": 65}},
                "avg_difficulty": 0.6,
                "completed_count": 3,
                "uncompleted_count": 0,
                "records": 3,
            },
            # Low records: records < 3
            {
                "task_name": "geography quiz",
                "avg_duration": {"0.5": {"count": 1, "avg": 40}},
                "avg_difficulty": 0.4,
                "completed_count": 1,
                "uncompleted_count": 0,
                "records": 1,
            },
            {
                "task_name": "art project",
                "avg_duration": {"0.0": {"count": 2, "avg": 20}},
                "avg_difficulty": 0.3,
                "completed_count": 2,
                "uncompleted_count": 1,
                "records": 2,
            },
            # Empty/NULL: cold start scenarios
            {
                "task_name": "new task one",
                "avg_difficulty": 0.5,
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "task_name": "new task two",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "task_name": "completely new task",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
        ]

        print("   Loading TaskMatcher model for vector generation...")
        matcher = TaskMatcher()

        task_stats_list = []
        for record in task_stats_records:
            task_name = record["task_name"]
            task_vector = matcher.model.encode(
                task_name, normalize_embeddings=True
            ).tolist()

            stats = TaskStatistics(
                task_name=task_name,
                task_name_vector=task_vector,
                avg_duration=record.get("avg_duration"),
                avg_duration_delta=record.get("avg_duration_delta"),
                avg_difficulty=record.get("avg_difficulty"),
                avg_difficulty_delta=record.get("avg_difficulty_delta"),
                completed_count=record.get("completed_count", 0),
                uncompleted_count=record.get("uncompleted_count", 0),
                records=record.get("records", 0),
                task_time_scores=record.get("task_time_scores"),
            )
            db.add(stats)
            task_stats_list.append(stats)

        db.flush()
        print(f"   Created {len(task_stats_list)} tasks_statistics records")

        # ============================================================
        # 4. CATEGORY_STATISTICS (10 records with variations)
        # ============================================================
        print("\n[4/7] Creating category_statistics...")

        category_stats_records = [
            # Full data (all buckets)
            {
                "category_name": "study",
                "avg_duration": {
                    "0.0": {"count": 5, "avg": 25},
                    "0.5": {"count": 8, "avg": 40},
                    "1.0": {"count": 4, "avg": 55},
                },
                "avg_duration_delta": {"0.5": {"count": 5, "avg": 8}},
                "avg_difficulty": 0.6,
                "avg_difficulty_delta": 0.08,
                "completed_count": 12,
                "uncompleted_count": 3,
                "records": 15,
                "category_time_scores": {"09:00": 2.2, "10:00": 1.9, "14:00": 2.0},
            },
            {
                "category_name": "fitness",
                "avg_duration": {
                    "0.5": {"count": 6, "avg": 45},
                    "1.0": {"count": 4, "avg": 60},
                },
                "avg_difficulty": 0.7,
                "completed_count": 8,
                "uncompleted_count": 2,
                "records": 10,
            },
            {
                "category_name": "work",
                "avg_duration": {
                    "0.0": {"count": 3, "avg": 30},
                    "0.5": {"count": 5, "avg": 50},
                },
                "avg_difficulty": 0.65,
                "completed_count": 7,
                "uncompleted_count": 1,
                "records": 8,
            },
            # Partial
            {
                "category_name": "personal",
                "avg_duration": {"0.5": {"count": 3, "avg": 35}},
                "avg_difficulty": 0.5,
                "completed_count": 3,
                "uncompleted_count": 1,
                "records": 4,
            },
            {
                "category_name": "reading",
                "avg_duration": {"0.0": {"count": 2, "avg": 20}},
                "avg_difficulty": 0.4,
                "completed_count": 2,
                "records": 2,
            },
            # Empty/NULL
            {
                "category_name": "coding",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "category_name": "shopping",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "category_name": "cooking",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "category_name": "gaming",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
            {
                "category_name": "music",
                "completed_count": 0,
                "uncompleted_count": 0,
                "records": 0,
            },
        ]

        cat_stats_list = []
        for record in category_stats_records:
            cat = (
                db.query(Category)
                .filter(Category.name == record["category_name"])
                .first()
            )
            stats = CategoryStatistics(
                category_id=cat.id,
                avg_duration=record.get("avg_duration"),
                avg_duration_delta=record.get("avg_duration_delta"),
                avg_difficulty=record.get("avg_difficulty"),
                avg_difficulty_delta=record.get("avg_difficulty_delta"),
                completed_count=record.get("completed_count", 0),
                uncompleted_count=record.get("uncompleted_count", 0),
                records=record.get("records", 0),
                category_time_scores=record.get("category_time_scores"),
            )
            db.add(stats)
            cat_stats_list.append(stats)

        db.flush()
        print(f"   Created {len(cat_stats_list)} category_statistics records")

        # ============================================================
        # 5. TASK_STATISTICS_LOCATIONS (10 records)
        # ============================================================
        print("\n[5/7] Creating task_statistics_locations...")

        # Link first 5 task_stats with varying locations
        for i in range(min(5, len(task_stats_list))):
            for j in range(2):  # 2 locations per task
                if i * 2 + j < 10:
                    loc = TaskStatisticsLocation(
                        statistics_id=task_stats_list[i].id,
                        location_id=locations[(i + j) % len(locations)].id,
                        count=10 - (i * 2 + j),  # Varying counts: 10, 9, 8...
                    )
                    db.add(loc)

        db.flush()
        print(f"   Created 10 task_statistics_locations records")

        # ============================================================
        # 6. CATEGORY_STATISTICS_LOCATIONS (10 records)
        # ============================================================
        print("\n[6/7] Creating category_statistics_locations...")

        # Link first 5 categories with varying locations
        for i in range(min(5, len(cat_stats_list))):
            for j in range(2):  # 2 locations per category
                if i * 2 + j < 10:
                    loc = CategoryStatisticsLocation(
                        statistics_id=cat_stats_list[i].id,
                        location_id=locations[(i + j) % len(locations)].id,
                        count=8 - (i * 2 + j),  # Varying counts
                    )
                    db.add(loc)

        db.flush()
        print(f"   Created 10 category_statistics_locations records")

        # ============================================================
        # 7. TASK_DRAFTS (5 records)
        # ============================================================
        print("\n[7/7] Creating task_drafts...")

        mock_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        draft_contents = [
            {
                "task": {
                    "name": "test task 1",
                    "duration": 60,
                    "difficulty": 0.5,
                    "category": ["study"],
                    "location": "home",
                    "importance": 0.6,
                },
                "match_result": {
                    "associated_id": str(task_stats_list[0].id),
                    "association_status": "same",
                    "name_vector": mock_vector,
                },
            },
            {
                "task": {
                    "name": "test task 2",
                    "duration": 45,
                    "difficulty": 0.7,
                    "category": ["fitness"],
                    "location": "gym",
                    "importance": 0.8,
                },
                "match_result": {
                    "associated_id": str(task_stats_list[1].id),
                    "association_status": "similar",
                    "name_vector": mock_vector,
                },
            },
            {
                "task": {
                    "name": "test task 3",
                    "duration": 30,
                    "difficulty": 0.3,
                    "category": ["work"],
                    "location": "office",
                    "importance": 0.5,
                },
                "match_result": {
                    "associated_id": None,
                    "association_status": "none",
                    "name_vector": None,
                },
            },
            {
                "task": {
                    "name": "new task from chat",
                    "duration": 50,
                    "difficulty": 0.6,
                    "category": ["personal"],
                    "location": "home",
                    "importance": 0.7,
                },
                "match_result": {
                    "associated_id": None,
                    "association_status": "none",
                    "name_vector": None,
                },
            },
            {
                "task": {
                    "name": "another test",
                    "duration": 25,
                    "difficulty": 0.4,
                    "category": ["reading"],
                    "location": "library",
                    "importance": 0.5,
                },
                "match_result": {
                    "associated_id": None,
                    "association_status": "none",
                    "name_vector": None,
                },
            },
        ]

        drafts = []
        for content in draft_contents:
            draft = TaskDraft(content=content)
            db.add(draft)
            drafts.append(draft)

        db.flush()
        print(f"   Created {len(drafts)} task_drafts records")

        # ============================================================
        # COMMIT
        # ============================================================
        db.commit()
        print("\n" + "=" * 60)
        print("Test data generated successfully!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Categories: {len(categories)}")
        print(f"  - Locations: {len(locations)}")
        print(f"  - TaskStatistics: {len(task_stats_list)}")
        print(f"  - CategoryStatistics: {len(cat_stats_list)}")
        print(f"  - TaskStatisticsLocations: 10")
        print(f"  - CategoryStatisticsLocations: 10")
        print(f"  - TaskDrafts: {len(drafts)}")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_all_data()
    generate_test_data()
