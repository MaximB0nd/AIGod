from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database.sqlite_setup import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | in_progress | done
    created_at = Column(DateTime(timezone=True), server_default=func.now())
