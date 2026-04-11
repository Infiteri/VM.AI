from sqlalchemy import Column, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Location(BaseModel):
    """
    Master location list.
    
    Each location can be associated with many tasks and statistics.
    Name is unique — no duplicate locations allowed.
    Examples: "home", "library", "office", "gym".
    """
    __tablename__ = "locations"

    name = Column(Text, nullable=False, unique=True)

    # Relationships
    task_statistics = relationship(
        "TaskStatisticsLocation",
        back_populates="location",
        cascade="all, delete-orphan",
        lazy="select",
    )
    category_statistics = relationship(
        "CategoryStatisticsLocation",
        back_populates="location",
        cascade="all, delete-orphan",
        lazy="select",
    )
