from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomCreate, RoomOut, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список комнат текущего пользователя."""
    rooms = db.query(Room).filter(Room.user_id == current_user.id).all()
    return rooms


@router.post("", response_model=RoomOut)
def create_room(
    room_data: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать комнату."""
    room = Room(name=room_data.name, user_id=current_user.id)
    db.add(room)
    db.flush()

    if room_data.agent_ids:
        agents = db.query(Agent).filter(Agent.id.in_(room_data.agent_ids)).all()
        if len(agents) != len(room_data.agent_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Один или несколько agent_id не найдены",
            )
        room.agents = agents

    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_id}", response_model=RoomOut)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить комнату по ID."""
    room = db.query(Room).filter(Room.id == room_id, Room.user_id == current_user.id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")
    return room


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    room_data: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить комнату."""
    room = db.query(Room).filter(Room.id == room_id, Room.user_id == current_user.id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")

    if room_data.name is not None:
        room.name = room_data.name
    if room_data.agent_ids is not None:
        agents = db.query(Agent).filter(Agent.id.in_(room_data.agent_ids)).all()
        if len(agents) != len(room_data.agent_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Один или несколько agent_id не найдены",
            )
        room.agents = agents

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить комнату."""
    room = db.query(Room).filter(Room.id == room_id, Room.user_id == current_user.id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Комната не найдена")
    db.delete(room)
    db.commit()
