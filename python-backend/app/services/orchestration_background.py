"""
Фоновый запуск оркестрации для комнат.

При первом сообщении в комнате с orchestration_type != "single"
создаётся OrchestrationClient, запускается в фоне, сообщения пользователя
попадают в user_message_queue; ответы агентов сохраняются в БД и рассылаются via WebSocket.
"""
import asyncio
from typing import Optional

from sqlalchemy.orm import Session

from app.database.sqlite_setup import SessionLocal
from app.models.agent import Agent
from app.models.message import Message as DBMessage
from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.message import Message
from app.services.agents_orchestration.message_type import MessageType
from app.services.orchestration_service import create_orchestration_client
from app.ws import broadcast_chat_message


def _agent_id_by_name(agents: list[Agent], name: str) -> Optional[int]:
    """Найти agent_id по имени."""
    for a in agents:
        if a.name == name:
            return a.id
    return None


def _make_message_callback(room_id: int, agents: list[Agent]):
    """Создать колбэк для сохранения и рассылки сообщений оркестрации."""

    async def on_message(msg: Message) -> None:
        # Сохраняем и рассылаем только AGENT/NARRATOR; USER уже сохранён в send_message
        if msg.type not in (MessageType.AGENT, MessageType.NARRATOR, MessageType.SUMMARIZED):
            if msg.type == MessageType.USER:
                # Пользовательское уже в БД
                pass
            return

        agent_id = _agent_id_by_name(agents, msg.sender)
        session: Session = SessionLocal()
        try:
            db_msg = DBMessage(
                room_id=room_id,
                agent_id=agent_id,
                text=msg.content,
                sender=msg.sender,
            )
            session.add(db_msg)
            session.commit()
            session.refresh(db_msg)

            payload = {
                "id": str(db_msg.id),
                "text": db_msg.text,
                "sender": db_msg.sender,
                "agentId": str(agent_id) if agent_id else None,
                "timestamp": db_msg.created_at.isoformat() if db_msg.created_at else "",
            }
            await broadcast_chat_message(room_id, payload)
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    return on_message


class OrchestrationRegistry:
    """Реестр фоновых оркестраций по room_id."""

    def __init__(self) -> None:
        self._clients: dict[int, OrchestrationClient] = {}
        self._tasks: dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def get_or_start(self, room) -> Optional[OrchestrationClient]:
        """
        Получить или запустить оркестрацию для комнаты.
        Возвращает None, если комнате не нужна оркестрация (single).
        """
        orchestration_type = getattr(room, "orchestration_type", None) or "single"
        if orchestration_type == "single":
            return None

        room_id = room.id
        async with self._lock:
            if room_id in self._clients:
                return self._clients[room_id]

            client = create_orchestration_client(room)
            if not client:
                return None

            callback = _make_message_callback(room_id, list(room.agents))
            client.on_message(callback)

            task = asyncio.create_task(client.start(max_ticks=None))
            self._clients[room_id] = client
            self._tasks[room_id] = task

        return client

    def get(self, room_id: int) -> Optional[OrchestrationClient]:
        """Получить клиент без создания."""
        return self._clients.get(room_id)

    async def stop_room(self, room_id: int) -> None:
        """Остановить оркестрацию комнаты."""
        async with self._lock:
            client = self._clients.pop(room_id, None)
            task = self._tasks.pop(room_id, None)
        if client and task:
            await client.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def stop_all(self) -> None:
        """Остановить все оркестрации (при shutdown)."""
        async with self._lock:
            clients = dict(self._clients)
            tasks = dict(self._tasks)
            self._clients.clear()
            self._tasks.clear()

        for room_id, client in clients.items():
            await client.stop()
        for task in tasks.values():
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)


# Глобальный реестр
registry = OrchestrationRegistry()
