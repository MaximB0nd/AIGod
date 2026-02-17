from sqlalchemy import Column, Float, ForeignKey, Integer

from app.database.sqlite_setup import Base


class Relationship(Base):
    __tablename__ = "relationships"

    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    agent1_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    agent2_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    sympathy_value = Column(Float, default=0.0)  # -1.0 .. +1.0
    interaction_count = Column(Integer, default=0)
