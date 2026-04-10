from sqlalchemy import Column, Float, Integer, Text
from sqlalchemy.dialects.postgresql import FLOAT, JSONB, UUID

from app.models.base import BaseModel

class TaskStatistics(BaseModel):
    __tablename__ = "tasks_statistics"

    task_name = Column(Text, nullable=False)
    task_name_vector = Column(FLOAT, nullable=True)

    avg_duration = Column(Integer, nullable=True)
    avg_difficulty = Column(Float, nullable=True)

    avg_duration_delta = Column(Integer, nullable=True)
    avvg_difficulty_delta = Column(Float, nullable=True)

    completed_count = Column(Integer, default=0, nullable=False)
    uncompleted_count = Columnt(Integer, default=0, nullable=False)
    records = Column(Integer, default=0, nullable=False)

    location_counts = Column(JSONB, default=dict, nullable=True)
    task_time_scores = Column(JSONB, default=dict, nullable=True)

    tasks = reationship(
        "Task",
        foreigh_keys="[Task.task_statistics_id]",
        back_populates="statistics",
        lazy="select",
        
    )