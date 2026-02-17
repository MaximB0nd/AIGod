"""Роуты для шаблонов агентов (default-agents). Клиент получает данные для предзаполнения формы."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db
from app.models.default_agent import DefaultAgent

router = APIRouter(prefix="/default-agents", tags=["default-agents"])


@router.get("")
def list_default_agents(db: Session = Depends(get_db)):
    """
    Список шаблонов агентов для выбора.
    Используется для отображения списка при создании агента по шаблону.
    """
    items = db.query(DefaultAgent).order_by(DefaultAgent.id).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "personality_preview": (d.personality[:80] + "...") if len(d.personality) > 80 else d.personality,
            "avatar_url": d.avatar_url,
        }
        for d in items
    ]


@router.get("/{default_agent_id}")
def get_default_agent(default_agent_id: int, db: Session = Depends(get_db)):
    """
    Получить шаблон агента по id.
    Возвращает данные в формате, готовом для POST /api/rooms/{roomId}/agents:
    name, character, avatar — клиент подставляет в форму и отправляет в ручку добавления агента.
    """
    d = db.query(DefaultAgent).filter(DefaultAgent.id == default_agent_id).first()
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон агента не найден")
    return {
        "id": d.id,
        "name": d.name,
        "character": d.personality,
        "avatar": d.avatar_url,
    }
