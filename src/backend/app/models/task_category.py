from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskCategory(Base):
    """
    Junction table: tasks ↔ categories (many-to-many).
    
    Priority determines ordering (1 = highest priority / most relevant).
    Composite primary key prevents duplicate task-category associations.
    """
    __tablename__ = "task_categories"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    priority = Column(Integer, nullable=False, default=1)

    # Relationships
    task = relationship(
        "Task",
        back_populates="task_categories",
        lazy="select",
    )
    category = relationship(
        "Category",
        back_populates="tasks",
        lazy="select",
    )
