from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db
from app.dependencies import get_current_user, get_room_for_user
from app.models.room import Room
from app.models.user import User
from app.schemas.api import (
    RoomCreateIn,
    RoomOut,
    RoomsListOut,
    RoomUpdateIn,
    SuccessOut,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=RoomsListOut)
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список комнат пользователя."""
    rooms = db.query(Room).filter(Room.user_id == current_user.id).all()
    return RoomsListOut(
        rooms=[RoomOut.from_room(r) for r in rooms]
    )


@router.post("", response_model=RoomOut)
def create_room(
    data: RoomCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать комнату."""
    room = Room(
        name=data.name,
        description=data.description,
        speed=1.0,
        user_id=current_user.id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return RoomOut.from_room(room)


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
    """Изменить комнату."""
    if data.name is not None:
        room.name = data.name
    if data.description is not None:
        room.description = data.description
    if data.speed is not None:
        room.speed = data.speed
    room.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return RoomOut.from_room(room)


@router.delete("/{room_id}", status_code=204)
def delete_room(
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Удалить комнату."""
    db.delete(room)
    db.commit()


# --- Вложенные роуты (agents, events, feed, relationships) ---
# Подключаются через include_router с prefix="/rooms"
