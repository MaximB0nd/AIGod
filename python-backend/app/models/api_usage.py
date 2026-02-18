"""
Учёт обращений к внешним API (Yandex GPT и др.) для ограничения расходов.
"""
from sqlalchemy import Column, Date, Integer
from sqlalchemy.sql import func

from app.database.sqlite_setup import Base


class ApiUsage(Base):
    """Счётчик вызовов API по дням. Один ряд = один день."""
    __tablename__ = "api_usage"

    usage_date = Column(Date, primary_key=True)  # дата в UTC
    call_count = Column(Integer, default=0, nullable=False)
