"""
Менеджер WebSocket-подключений по комнатам.

Два независимых пула: chat (чат/события) и graph (граф отношений).
Каждый клиент подключается к комнате — при изменениях сервер рассылает всем в комнате.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Управление подключениями по комнатам.
    room_id -> set of WebSocket
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room_id: int) -> None:
        """Регистрирует подключение к комнате."""
        await self._lock.acquire()
        try:
            self._connections[room_id].add(websocket)
            logger.info("%s: client connected to room %s, total=%d", self.name, room_id, len(self._connections[room_id]))
        finally:
            self._lock.release()

    async def disconnect(self, websocket: WebSocket, room_id: int) -> None:
        """Удаляет подключение."""
        async with self._lock:
            conns = self._connections.get(room_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    del self._connections[room_id]
            logger.info("%s: client disconnected from room %s", self.name, room_id)

    async def broadcast(self, room_id: int, message: dict[str, Any]) -> None:
        """
        Рассылает сообщение всем подключённым клиентам в комнате.
        Отключившиеся исключаются из пула.
        """
        async with self._lock:
            conns = set(self._connections.get(room_id, []))  # copy

        if not conns:
            logger.warning("%s: broadcast room_id=%s — 0 подключений, сообщение не доставлено", self.name, room_id)
            return

        logger.info("%s: broadcast room_id=%s msg_type=%s → %d клиентов", self.name, room_id, message.get("type"), len(conns))
        dead: set[WebSocket] = set()
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning("%s: send failed for room %s: %s", self.name, room_id, e)
                dead.add(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.get(room_id, set()).discard(ws)


# Глобальные менеджеры (singleton)
chat_manager = ConnectionManager("chat")
graph_manager = ConnectionManager("graph")
