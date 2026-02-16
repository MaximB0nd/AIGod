from sqlalchemy import Column, Integer, Float, ForeignKey
from ..database.sqlite_setup import Base

class relationship(Base):
    __tablename__ = "relationships"

    agent1_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    agent2_id = Column(Integer, ForeignKey("agents.id"), primary_key=True)
    sympathy_value = Column(Float, default=0.0)     # -1.0 .. +1.0
    interaction_count = Column(Integer, default=0)
