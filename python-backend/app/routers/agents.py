from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db
from app.models.agent import Agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", summary="Список агентов")
def get_all_agents(db: Session = Depends(get_db)):
    """Получить всех агентов из базы."""
    agents = db.query(Agent).all()
    if not agents:
        return {"message": "Агенты не найдены", "count": 0}

    return [
        {
            "id": agent.id,
            "name": agent.name,
            "personality": agent.personality[:80] + "..." if len(agent.personality) > 80 else agent.personality,
            "avatar_url": agent.avatar_url or "(нет аватара)",
            "state_vector": agent.state_vector,
        }
        for agent in agents
    ]
