from sqlalchemy import Column, Integer, String

from app.database.sqlite_setup import Base


class DefaultAgent(Base):
    """Шаблон агента для выбора при создании. Данные для предзаполнения формы."""
    __tablename__ = "default_agents"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    personality = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
