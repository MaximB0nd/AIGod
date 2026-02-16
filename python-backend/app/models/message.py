from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from ..database.sqlite_setup import Base

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    text = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    is_system = Column(Boolean, default=False)