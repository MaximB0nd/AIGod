from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.sqlite_setup import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False, default="user_event")
    description = Column(String, nullable=False)
    agent_ids = Column(JSON, default=list)  # список id агентов
    mood_impact = Column(JSON, default=dict)  # {agentId: delta}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
