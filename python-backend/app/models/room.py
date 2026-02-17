from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.sqlite_setup import Base

# Таблица связи Room <-> Agent (many-to-many)
# В каждой комнате агенты уникальны (один агент — один раз в комнате)
room_agents = Table(
    "room_agents",
    Base.metadata,
    Column("room_id", Integer, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
    Column("agent_id", Integer, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("room_id", "agent_id", name="uq_room_agent"),
)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    speed = Column(Float, default=1.0)  # 1.0 = нормальная скорость
    orchestration_type = Column(String, default="single", nullable=False)  # single | circular | narrator | full_context
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="rooms")
    agents = relationship(
        "Agent",
        secondary=room_agents,
        back_populates="rooms",
        lazy="selectin",
    )
