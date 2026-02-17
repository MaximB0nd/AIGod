"""
Функции рассылки в WebSocket.

Вызываются из HTTP-роутов при создании сообщений, событий, изменении отношений.
"""
import logging

from app.ws.manager import chat_manager, graph_manager

logger = logging.getLogger("aigod.ws.broadcast")


async def broadcast_chat_message(room_id: int, payload: dict) -> None:
    """
    Рассылает новое сообщение в чат комнаты всем подключённым клиентам.
    payload: { id, text, sender, agentId?, timestamp, agentResponse? }
    """
    full_payload = {"type": "message", "payload": payload}
    logger.info(
        "broadcast_chat_message room_id=%s id=%s sender=%s text_len=%d",
        room_id, payload.get("id"), payload.get("sender"), len(str(payload.get("text", ""))),
    )
    await chat_manager.broadcast(room_id, full_payload)


async def broadcast_chat_event(room_id: int, payload: dict) -> None:
    """
    Рассылает событие в комнату всем подключённым клиентам.
    payload: { id, eventType, agentIds, description, timestamp, moodImpact? }
    """
    logger.info(
        "broadcast_chat_event room_id=%s eventType=%s id=%s",
        room_id, payload.get("eventType"), payload.get("id"),
    )
    await chat_manager.broadcast(room_id, {"type": "event", "payload": payload})


async def broadcast_graph_edge(room_id: int, from_agent_id: str, to_agent_id: str, sympathy_level: float) -> None:
    """
    Рассылает обновление ребра графа всем подключённым клиентам.
    Клиент обновит D3.js / vis-network без перезапроса всего графа.
    """
    logger.info(
        "broadcast_graph_edge room_id=%s from=%s to=%s sympathy=%.2f",
        room_id, from_agent_id, to_agent_id, sympathy_level,
    )
    await graph_manager.broadcast(
        room_id,
        {
            "type": "edge_update",
            "payload": {
                "roomId": str(room_id),
                "from": from_agent_id,
                "to": to_agent_id,
                "sympathyLevel": sympathy_level,
            },
        },
    )
