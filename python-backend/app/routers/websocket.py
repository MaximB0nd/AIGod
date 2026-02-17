"""
WebSocket для реального времени в комнате.

1. /chat — сообщения от агентов и системные события
2. /graph — обновления графа отношений (id комнаты, id агентов, коэффициент)

Пользователь — наблюдатель (демиург). Один клиент на комнату.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import config
from app.database.sqlite_setup import SessionLocal
from jose import JWTError, jwt
from app.models.room import Room
from app.ws import chat_manager, graph_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rooms", tags=["websocket"])


def _verify_token(token: Optional[str]) -> Optional[str]:
    """Валидация JWT. Возвращает email при успехе, иначе None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _check_room_access(room_id: int, user_email: str) -> bool:
    """Проверяет, что пользователь имеет доступ к комнате."""
    from app.models.user import User

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return False
        room = db.query(Room).filter(Room.id == room_id, Room.user_id == user.id).first()
        return room is not None


async def _reject_and_close(websocket: WebSocket, code: int, reason: str) -> None:
    """Отклоняет подключение и закрывает сокет."""
    await websocket.close(code=code, reason=reason[:123])  # reason max 123 bytes


# --- Чат ---

@router.websocket("/{room_id}/chat")
async def room_chat(
    websocket: WebSocket,
    room_id: int,
    token: Optional[str] = Query(None, description="JWT из /api/auth/login"),
):
    """
    WebSocket чата комнаты: сообщения от агентов и системные события.

    Подключение: ws://host/api/rooms/{roomId}/chat?token=JWT
    """
    # Проверка токена
    email = _verify_token(token)
    if not email:
        await _reject_and_close(websocket, 4001, "Unauthorized: token required")
        return

    if not _check_room_access(room_id, email):
        await _reject_and_close(websocket, 4003, "Forbidden: no access to room")
        return

    await websocket.accept()
    await chat_manager.connect(websocket, room_id)

    try:
        # Подтверждение подключения
        await websocket.send_json({
            "type": "connected",
            "payload": {"roomId": str(room_id), "message": "Подключено к чату комнаты"},
        })

        while True:
            data = await websocket.receive_text()
            # Ping для поддержания соединения
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
            except (json.JSONDecodeError, TypeError):
                pass
            # Игнорируем остальные входящие (клиент только наблюдает)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("chat ws error room=%s: %s", room_id, e)
        try:
            await websocket.send_json({"type": "error", "payload": {"message": str(e)}})
        except Exception:
            pass
    finally:
        await chat_manager.disconnect(websocket, room_id)


# --- Граф отношений ---

@router.websocket("/{room_id}/graph")
async def room_graph(
    websocket: WebSocket,
    room_id: int,
    token: Optional[str] = Query(None, description="JWT из /api/auth/login"),
):
    """
    WebSocket графа отношений: обновления рёбер (agent1, agent2, sympathyLevel).

    Подключение: ws://host/api/rooms/{roomId}/graph?token=JWT

    Формат обновления:
    { "type": "edge_update", "payload": { "roomId": "1", "from": "1", "to": "2", "sympathyLevel": 0.7 } }
    """
    email = _verify_token(token)
    if not email:
        await _reject_and_close(websocket, 4001, "Unauthorized: token required")
        return

    if not _check_room_access(room_id, email):
        await _reject_and_close(websocket, 4003, "Forbidden: no access to room")
        return

    await websocket.accept()
    await graph_manager.connect(websocket, room_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "payload": {"roomId": str(room_id), "message": "Подключено к графу отношений"},
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("graph ws error room=%s: %s", room_id, e)
        try:
            await websocket.send_json({"type": "error", "payload": {"message": str(e)}})
        except Exception:
            pass
    finally:
        await graph_manager.disconnect(websocket, room_id)
