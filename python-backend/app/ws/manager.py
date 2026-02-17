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

logger = logging.getLogger("aigod.ws.manager")


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
            total = len(self._connections[room_id])
            total_conns = sum(len(s) for s in self._connections.values())
            logger.info(
                "WS [%s] connect room_id=%s total_in_room=%d total_all=%d",
                self.name, room_id, total, total_conns,
            )
        finally:
            self._lock.release()

    async def disconnect(self, websocket: WebSocket, room_id: int) -> None:
        """Удаляет подключение."""
        async with self._lock:
            conns = self._connections.get(room_id)
            if conns:
                conns.discard(websocket)
                remaining = len(conns) if conns else 0
                if not conns:
                    del self._connections[room_id]
                logger.info(
                    "WS [%s] disconnect room_id=%s remaining=%d",
                    self.name, room_id, remaining,
                )
            else:
                logger.info("WS [%s] disconnect room_id=%s (уже отключён)", self.name, room_id)

    async def broadcast(self, room_id: int, message: dict[str, Any]) -> None:
        """
        Рассылает сообщение всем подключённым клиентам в комнате.
        Отключившиеся исключаются из пула.
        """
        async with self._lock:
            conns = set(self._connections.get(room_id, []))  # copy

        if not conns:
            logger.warning(
                "WS [%s] broadcast room_id=%s type=%s — 0 подключений, сообщение не доставлено",
                self.name, room_id, message.get("type"),
            )
            return

        msg_type = message.get("type")
        payload_preview = ""
        if "payload" in message:
            p = message["payload"]
            if isinstance(p, dict):
                payload_preview = " id=%s sender=%s" % (str(p.get("id", "")), str(p.get("sender", "")))
        logger.info(
            "WS [%s] broadcast room_id=%s type=%s → %d клиентов%s",
            self.name, room_id, msg_type, len(conns), payload_preview,
        )
        dead: set[WebSocket] = set()
        for ws in conns:
            try:
                await ws.send_json(message)
                logger.debug("WS [%s] send_json OK room_id=%s type=%s", self.name, room_id, msg_type)
            except Exception as e:
                logger.warning("WS [%s] send_json FAIL room_id=%s: %s", self.name, room_id, e)
                dead.add(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.get(room_id, set()).discard(ws)


# Глобальные менеджеры (singleton)
chat_manager = ConnectionManager("chat")
graph_manager = ConnectionManager("graph")
