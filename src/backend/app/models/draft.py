from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base

class TaskDraft(Base):
    __tablename__ = "task_drafts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    content = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False
    )