from sqlalchemy import Column, Integer, String, JSON
from ..database.sqlite_setup import Base

# Модель таблицы Agent (персонажей в комнате).
# Будет заполнена 6 персонажеми

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    personality = Column(String, nullable=False)
    state_vector = Column(JSON, default=dict)  # эмоции и т.п.