"""
SQLAlchemy ORM Models.

Importing this package registers all models with SQLAlchemy's metadata,
which Alembic needs to generate migrations.
"""

from app.models.base import BaseModel
from app.models.category import Category
from app.models.task_category import TaskCategory
from app.models.location import Location
from app.models.task import Task
from app.models.statistics import (
    TaskStatistics,
    CategoryStatistics,
    TaskStatisticsLocation,
    CategoryStatisticsLocation,
)
from app.models.schedule import MainScheduleSlot, ProvisionalSlot
from app.models.workflow import UnscheduledTask, ScheduleChange

__all__ = [
    "BaseModel",
    "Category",
    "TaskCategory",
    "Location",
    "Task",
    "TaskStatistics",
    "CategoryStatistics",
    "TaskStatisticsLocation",
    "CategoryStatisticsLocation",
    "MainScheduleSlot",
    "ProvisionalSlot",
    "UnscheduledTask",
    "ScheduleChange",
]
