from sqlalchemy import Column, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Category(BaseModel):
    """
    Master category list.

    Each category can be associated with many tasks.
    Name is unique — no duplicate categories allowed.
    Pre-seeded values: study, fitness, work, personal.
    """

    __tablename__ = "categories"

    name = Column(Text, nullable=False, unique=True)

    # Relationships
    tasks = relationship(
        "TaskCategory",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select",
    )
    statistics = relationship(
        "CategoryStatistics",
        back_populates="category",
        uselist=False,
    )
