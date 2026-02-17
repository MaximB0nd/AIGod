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

logger = logging.getLogger("aigod.ws.router")

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
    logger.warning("WS reject code=%s reason=%s", code, reason)
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
    logger.info("WS chat: попытка подключения room_id=%s token=%s", room_id, "yes" if token else "no")
    email = _verify_token(token)
    if not email:
        logger.warning("WS chat: room_id=%s токен невалиден или отсутствует", room_id)
        await _reject_and_close(websocket, 4001, "Unauthorized: token required")
        return

    if not _check_room_access(room_id, email):
        logger.warning("WS chat: room_id=%s доступ запрещён для %s", room_id, email)
        await _reject_and_close(websocket, 4003, "Forbidden: no access to room")
        return

    await websocket.accept()
    logger.info("WS chat: accept room_id=%s", room_id)
    await chat_manager.connect(websocket, room_id)

    try:
        await websocket.send_json({
            "type": "connected",
            "payload": {"roomId": str(room_id), "message": "Подключено к чату комнаты"},
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
                    logger.debug("WS chat: ping→pong room_id=%s", room_id)
                else:
                    logger.debug("WS chat: received room_id=%s type=%s", room_id, msg.get("type"))
            except (json.JSONDecodeError, TypeError):
                logger.debug("WS chat: received raw room_id=%s len=%d", room_id, len(data))
    except WebSocketDisconnect:
        logger.info("WS chat: disconnect room_id=%s (клиент отключился)", room_id)
    except Exception as e:
        logger.exception("WS chat error room_id=%s: %s", room_id, e)
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
    logger.info("WS graph: попытка подключения room_id=%s", room_id)
    email = _verify_token(token)
    if not email:
        await _reject_and_close(websocket, 4001, "Unauthorized: token required")
        return

    if not _check_room_access(room_id, email):
        await _reject_and_close(websocket, 4003, "Forbidden: no access to room")
        return

    await websocket.accept()
    logger.info("WS graph: accept room_id=%s", room_id)
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
                    logger.debug("WS graph: ping→pong room_id=%s", room_id)
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        logger.info("WS graph: disconnect room_id=%s", room_id)
    except Exception as e:
        logger.exception("WS graph error room_id=%s: %s", room_id, e)
        try:
            await websocket.send_json({"type": "error", "payload": {"message": str(e)}})
        except Exception:
            pass
    finally:
        await graph_manager.disconnect(websocket, room_id)
