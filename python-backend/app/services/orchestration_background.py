"""
Фоновый запуск оркестрации для комнат.

При первом сообщении в комнате с orchestration_type != "single"
создаётся OrchestrationClient, запускается в фоне, сообщения пользователя
попадают в user_message_queue (UserMessageEvent); ответы агентов сохраняются
в БД и рассылаются via WebSocket.

Pipeline: User → POST /messages → enqueue_user_message → strategy → agents reply → broadcast
"""
import asyncio
import logging
from datetime import datetime
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

logger = logging.getLogger("aigod.orchestration")


def _load_room_history(room_id: int, agents: list[Agent], limit: int = 20) -> list[Message]:
    """
    Загрузить историю сообщений комнаты из БД в формат оркестрации.
    Orchestration получает контекст чата комнаты для корректного ответа.
    """
    session = SessionLocal()
    try:
        rows = (
            session.query(DBMessage)
            .filter(DBMessage.room_id == room_id)
            .order_by(DBMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        result = []
        for m in rows:
            msg_type = MessageType.USER if m.sender == "user" or m.agent_id is None else MessageType.AGENT
            result.append(
                Message(
                    content=m.text,
                    type=msg_type,
                    sender=m.sender,
                    timestamp=m.created_at or datetime.now(),
                )
            )
        logger.info("orchestration: load_room_history room_id=%s загружено %d сообщений", room_id, len(result))
        return result
    finally:
        session.close()


def _agent_id_by_name(agents: list[Agent], name: str) -> Optional[int]:
    """Найти agent_id по имени."""
    for a in agents:
        if a.name == name:
            return a.id
    return None


def _make_message_callback(room_id: int, agents: list[Agent]):
    """Создать колбэк для сохранения, рассылки, памяти и обновления графа отношений."""

    async def on_message(msg: Message) -> None:
        if msg.type not in (MessageType.AGENT, MessageType.NARRATOR, MessageType.SUMMARIZED):
            logger.debug("orchestration on_message room_id=%s skip type=%s", room_id, msg.type)
            return

        agent_id = _agent_id_by_name(agents, msg.sender)
        logger.info("orchestration on_message room_id=%s type=%s sender=%s agent_id=%s", room_id, msg.type, msg.sender, agent_id)
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
            logger.info("orchestration on_message room_id=%s сохранено msg_id=%s broadcast OK", room_id, db_msg.id)
        except Exception as e:
            logger.exception("orchestration on_message room_id=%s ошибка: %s", room_id, e)
            session.rollback()
            raise
        finally:
            session.close()

        # Обновить граф отношений (эвристический анализатор)
        try:
            from app.models.room import Room
            from app.database.sqlite_setup import SessionLocal
            from app.services.relationship_model_service import get_relationship_manager
            s = SessionLocal()
            try:
                room = s.query(Room).filter(Room.id == room_id).first()
                if room and room.agents:
                    mgr = get_relationship_manager(room)
                    agent_names = [a.name for a in room.agents]
                    await mgr.process_message(
                        message=msg.content,
                        sender=msg.sender,
                        participants=agent_names,
                    )
                    logger.debug("orchestration graph updated room_id=%s sender=%s", room_id, msg.sender)
            finally:
                s.close()
        except Exception as e:
            logger.debug("orchestration graph update failed: %s", e)

        # Сохранить в память (user_msg + agent_msg) если есть последний запрос пользователя
        try:
            client = registry.get(room_id)
            if client and client.context:
                from app.services.room_services_registry import get_memory_integration
                from app.services.context_memory.models import ImportanceLevel
                from app.models.room import Room
                s2 = SessionLocal()
                try:
                    room = s2.query(Room).filter(Room.id == room_id).first()
                    if room:
                        integration = get_memory_integration(room)
                        if integration:
                            user_msgs = [
                                m for m in client.context.history
                                if m.type == MessageType.USER or (m.sender or "").lower() in ("user", "пользователь")
                            ]
                            last_user = user_msgs[-1].content if user_msgs else None
                            if last_user:
                                text = f"User: {last_user}\n{msg.sender}: {msg.content}"
                                await integration.memory_manager.add_message(
                                    content=text,
                                    sender=msg.sender,
                                    importance=ImportanceLevel.MEDIUM,
                                    metadata={"room_id": room_id, "pipeline": "orchestration"},
                                )
                                logger.debug("orchestration memory stored room_id=%s", room_id)
                finally:
                    s2.close()
        except Exception as e:
            logger.debug("orchestration memory store failed: %s", e)

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
            logger.debug("orchestration get_or_start room_id=%s skip (single)", room.id)
            return None

        room_id = room.id
        async with self._lock:
            if room_id in self._clients:
                logger.info("orchestration get_or_start room_id=%s уже запущена", room_id)
                return self._clients[room_id]

            logger.info("orchestration get_or_start room_id=%s создаём клиент type=%s", room_id, orchestration_type)
            client = create_orchestration_client(room)
            if not client:
                logger.warning("orchestration get_or_start room_id=%s create_orchestration_client вернул None", room_id)
                return None

            room_history = _load_room_history(room_id, list(room.agents))
            for msg in room_history:
                client.context.add_message(msg)

            callback = _make_message_callback(room_id, list(room.agents))
            client.on_message(callback)

            task = asyncio.create_task(client.start(max_ticks=None))
            self._clients[room_id] = client
            self._tasks[room_id] = task
            logger.info("orchestration get_or_start room_id=%s ЗАПУЩЕНО agents=%s", room_id, [a.name for a in room.agents])

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
            logger.info("orchestration stop_room room_id=%s", room_id)
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

        logger.info("orchestration stop_all rooms=%s", list(clients.keys()))
        for room_id, client in clients.items():
            await client.stop()
        for task in tasks.values():
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)


# Глобальный реестр
registry = OrchestrationRegistry()


async def enqueue_room_run(room_id: int, text: str, sender: str = "user", room=None) -> bool:
    """
    Триггер оркестрации: поставить сообщение пользователя в очередь.

    Вызывать после сохранения сообщения в БД. Запускает оркестратор (если ещё не запущен)
    и кладёт UserMessageEvent в очередь. Без этого вызова агенты не получат сообщение.

    Args:
        room_id: ID комнаты
        text: Текст сообщения
        sender: Отправитель (по умолчанию "user")
        room: Объект Room (опционально, для избежания доп. запроса)

    Returns:
        True если оркестрация активна и сообщение в очереди, False иначе (single mode).
    """
    if room is None:
        from app.database.sqlite_setup import SessionLocal
        from app.models.room import Room
        session = SessionLocal()
        try:
            room = session.query(Room).filter(Room.id == room_id).first()
        finally:
            session.close()

    if not room or not getattr(room, "agents", None) or not room.agents:
        return False

    orchestration_type = getattr(room, "orchestration_type", None) or "single"
    if orchestration_type == "single":
        logger.debug("enqueue_room_run room_id=%s skip (single)", room_id)
        return False

    client = await registry.get_or_start(room)
    if client:
        await client.enqueue_user_message(room_id, text, sender)
        logger.info("enqueue_room_run room_id=%s enqueued text_len=%d sender=%s", room_id, len(text), sender)
        return True
    logger.warning("enqueue_room_run room_id=%s client=None, не удалось поставить в очередь", room_id)
    return False
