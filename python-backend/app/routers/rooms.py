import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger("aigod.rooms")
from sqlalchemy.orm import Session

from app.constants import NARRATOR_AGENT_NAME, NARRATOR_PERSONALITY
from app.database.sqlite_setup import get_db
from app.dependencies import get_current_user, get_room_for_user
from app.models.agent import Agent
from app.models.event import Event
from app.models.message import Message
from app.models.relationship import Relationship
from app.models.room import Room
from app.models.user import User
from app.services.orchestration_background import registry
from app.schemas.api import (
    RoomCreateIn,
    RoomOut,
    RoomsListOut,
    RoomUpdateIn,
    SuccessOut,
)

# Endpoints для комнат

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("", response_model=RoomsListOut)
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список комнат пользователя."""
    rooms = db.query(Room).filter(Room.user_id == current_user.id).all()
    logger.info("GET /rooms user_id=%s → %d комнат", current_user.id, len(rooms))
    return RoomsListOut(
        rooms=[RoomOut.from_room(r) for r in rooms]
    )


def _ensure_narrator_agent_in_room(room: Room, current_user: User, db: Session) -> None:
    """Добавить агента «Рассказчик» в комнату при circular/narrator/full_context (видимый агент)."""
    ot = getattr(room, "orchestration_type", None) or "single"
    if ot not in ("circular", "narrator", "full_context"):
        return
    if any(a.name == NARRATOR_AGENT_NAME for a in room.agents):
        return
    agent = Agent(
        name=NARRATOR_AGENT_NAME,
        personality=NARRATOR_PERSONALITY,
        avatar_url=None,
        state_vector={"mood": "neutral", "mood_level": 0.5},
        user_id=current_user.id,
    )
    db.add(agent)
    db.flush()
    room.agents.append(agent)
    db.commit()
    db.refresh(room)
    logger.info("Added Narrator agent to room_id=%s", room.id)


@router.post("", response_model=RoomOut)
def create_room(
    data: RoomCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать комнату. Клиент выбирает orchestration_type при создании. При narrator/full_context/circular — автоматически добавляется агент «Рассказчик» (пользователь его видит)."""
    room = Room(
        name=data.name,
        description=data.description,
        speed=1.0,
        orchestration_type=data.orchestration_type,
        user_id=current_user.id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    _ensure_narrator_agent_in_room(room, current_user, db)
    db.refresh(room)
    logger.info("POST /rooms created room_id=%s name=%s orchestration=%s", room.id, room.name, data.orchestration_type)
    return RoomOut.from_room(room, agent_count=len(room.agents))


@router.get("/{room_id}", response_model=RoomOut)
def get_room(
    room: Room = Depends(get_room_for_user),
):
    """Информация о комнате."""
    return RoomOut.from_room(room, agent_count=len(room.agents))


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(
    data: RoomUpdateIn,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Изменить описание и/или скорость комнаты."""
    if data.description is not None:
        room.description = data.description
    if data.speed is not None:
        room.speed = data.speed
    room.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return RoomOut.from_room(room)


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Удалить комнату и все её данные: сообщения, события, оркестрация."""
    room_id = room.id
    # Остановить оркестрацию
    await registry.stop_room(room_id)
    # Явно удалить сообщения и события чата (CASCADE может не сработать без PRAGMA foreign_keys)
    db.query(Message).filter(Message.room_id == room_id).delete(synchronize_session=False)
    db.query(Event).filter(Event.room_id == room_id).delete(synchronize_session=False)
    db.query(Relationship).filter(Relationship.room_id == room_id).delete(synchronize_session=False)
    db.delete(room)
    db.commit()
    logger.info("Удалена комната room_id=%s (сообщения, события, оркестрация)", room_id)


# --- Вложенные роуты (agents, events, feed, relationships) ---
# Подключаются через include_router с prefix="/rooms"
