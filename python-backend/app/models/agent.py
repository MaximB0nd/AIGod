from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database.sqlite_setup import Base


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    personality = Column(String, nullable=False)
    state_vector = Column(JSON, default=dict)  # mood: {mood, level, icon, color}
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    rooms = relationship("Room", secondary="room_agents", back_populates="agents")