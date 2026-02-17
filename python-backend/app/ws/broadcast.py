"""
Функции рассылки в WebSocket.

Вызываются из HTTP-роутов при создании сообщений, событий, изменении отношений.
"""
from app.ws.manager import chat_manager, graph_manager


async def broadcast_chat_message(room_id: int, payload: dict) -> None:
    """
    Рассылает новое сообщение в чат комнаты всем подключённым клиентам.
    payload: { id, text, sender, agentId?, timestamp, agentResponse? }
    """
    await chat_manager.broadcast(room_id, {"type": "message", "payload": payload})


async def broadcast_chat_event(room_id: int, payload: dict) -> None:
    """
    Рассылает событие в комнату всем подключённым клиентам.
    payload: { id, eventType, agentIds, description, timestamp, moodImpact? }
    """
    await chat_manager.broadcast(room_id, {"type": "event", "payload": payload})


async def broadcast_graph_edge(room_id: int, from_agent_id: str, to_agent_id: str, sympathy_level: float) -> None:
    """
    Рассылает обновление ребра графа всем подключённым клиентам.
    Клиент обновит D3.js / vis-network без перезапроса всего графа.
    """
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
