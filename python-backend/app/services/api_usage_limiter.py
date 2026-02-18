"""
Ограничение обращений к Yandex API для защиты от перерасхода средств.

Проверяет лимит перед каждым вызовом и записывает использование в БД.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.sqlite_setup import SessionLocal
from app.models.api_usage import ApiUsage

logger = logging.getLogger("aigod.api_usage")

_DEFAULT_LIMIT = 100  # защита по умолчанию


# Лимит из env. По умолчанию 100 — без лимита можно прогореть на API
def _get_limit_per_day() -> int:
    import os
    val = os.getenv("API_MESSAGE_LIMIT_PER_DAY", str(_DEFAULT_LIMIT)).strip()
    try:
        return max(0, int(val)) if val else _DEFAULT_LIMIT
    except ValueError:
        return _DEFAULT_LIMIT


def _get_limit_per_hour() -> int:
    import os
    return int(os.getenv("API_MESSAGE_LIMIT_PER_HOUR", "0"))


class ApiLimitExceededError(Exception):
    """Лимит обращений к API исчерпан."""
    def __init__(self, message: str, limit: int, current: int, window: str):
        super().__init__(message)
        self.limit = limit
        self.current = current
        self.window = window


def check_can_call_api() -> None:
    """
    Проверить, можно ли выполнить вызов API. Вызывает ApiLimitExceededError при превышении лимита.
    """
    limit_day = _get_limit_per_day()
    limit_hour = _get_limit_per_hour()
    if limit_day <= 0 and limit_hour <= 0:
        return

    session: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today = now.date()

        if limit_day > 0:
            row = session.query(ApiUsage).filter(ApiUsage.usage_date == today).first()
            count_today = row.call_count if row else 0
            if count_today >= limit_day:
                raise ApiLimitExceededError(
                    f"Дневной лимит API исчерпан ({count_today}/{limit_day})",
                    limit=limit_day,
                    current=count_today,
                    window="day",
                )
        # Почасовой лимит требует отдельной таблицы или поля — упростим: только дневной
    finally:
        session.close()


def record_api_call() -> int:
    """
    Записать факт вызова API. Возвращает текущее количество вызовов за сегодня (UTC).
    """
    limit_day = _get_limit_per_day()
    if limit_day <= 0:
        return 0

    session: Session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        row = session.query(ApiUsage).filter(ApiUsage.usage_date == today).first()
        if row:
            row.call_count += 1
            count = row.call_count
        else:
            session.add(ApiUsage(usage_date=today, call_count=1))
            count = 1
        session.commit()
        logger.info("API usage: today=%s count=%d limit=%d", today, count, limit_day)
        return count
    except Exception as e:
        session.rollback()
        logger.warning("record_api_call failed: %s", e)
        return 0
    finally:
        session.close()


def get_usage_stats() -> dict:
    """Статистика использования API за сегодня (UTC) и лимиты."""
    session: Session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        row = session.query(ApiUsage).filter(ApiUsage.usage_date == today).first()
        count_today = row.call_count if row else 0
        limit_day = _get_limit_per_day()
        return {
            "today": str(today),
            "callCount": count_today,
            "limitPerDay": limit_day if limit_day > 0 else None,
            "remaining": (limit_day - count_today) if limit_day > 0 else None,
            "limitExceeded": limit_day > 0 and count_today >= limit_day,
        }
    finally:
        session.close()
