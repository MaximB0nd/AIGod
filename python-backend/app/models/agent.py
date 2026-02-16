from sqlalchemy import Column, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database.sqlite_setup import Base


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    personality = Column(String, nullable=False)
    state_vector = Column(JSON, default=dict)

    rooms = relationship("Room", secondary="room_agents", back_populates="agents")