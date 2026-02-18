"""
Оркестрация через единый pipeline executor.

Каждый запрос ОБЯЗАТЕЛЬНО проходит:
RETRIEVE_MEMORY → PLAN → DISCUSS → SYNTHESIZE → STORE_MEMORY → UPDATE_GRAPH → DONE

Pipeline: User → POST /messages → run_pipeline_executor → этапы → broadcast
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
from app.services.orchestration.executor import PipelineExecutor
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
    """Колбэк: сохранить в БД и broadcast. Память и граф — в этапах pipeline."""
    async def on_message(msg: Message) -> None:
        if msg.type not in (MessageType.AGENT, MessageType.NARRATOR, MessageType.SUMMARIZED, MessageType.SYSTEM):
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

            # SQL Memory — мост для API keyMemories (только для агентов комнаты)
            if agent_id and msg.content and msg.type == MessageType.AGENT:
                try:
                    from app.models.memory import Memory
                    m = Memory(
                        agent_id=agent_id,
                        room_id=room_id,
                        content=msg.content[:2000] if len(msg.content) > 2000 else msg.content,
                        importance=0.6,
                    )
                    session.add(m)
                    session.commit()
                except Exception as e:
                    logger.warning("orchestration SQL Memory write failed: %s", e)
                    session.rollback()

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
        """Остановить оркестрацию комнаты (long-running client). Pipeline отменяется через cancel_pipeline_task."""
        async with self._lock:
            client = self._clients.pop(room_id, None)
            task = self._tasks.pop(room_id, None)
        if client and task:
            logger.info("orchestration stop_room room_id=%s (registry client)", room_id)
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

# Задачи pipeline по room_id (для stop)
_pipeline_tasks: dict[int, asyncio.Task] = {}
_pipeline_lock: asyncio.Lock | None = None


def _get_pipeline_lock() -> asyncio.Lock:
    global _pipeline_lock
    if _pipeline_lock is None:
        _pipeline_lock = asyncio.Lock()
    return _pipeline_lock


async def run_pipeline_executor(room_id: int, text: str, sender: str = "user", room=None) -> bool:
    """
    Единая точка входа: запустить pipeline executor.

    Каждый запрос ОБЯЗАТЕЛЬНО проходит: RETRIEVE_MEMORY → PLAN → DISCUSS → SYNTHESIZE → STORE_MEMORY → UPDATE_GRAPH.

    Returns:
        True если pipeline запущен, False иначе (single mode).
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
        logger.debug("run_pipeline_executor room_id=%s skip (single)", room_id)
        return False

    from app.services.orchestration_service import create_pipeline_components
    components = create_pipeline_components(room)
    if not components:
        logger.warning("run_pipeline_executor room_id=%s components=None", room_id)
        return False

    agents = list(room.agents)
    callback = _make_message_callback(room_id, agents)

    # Загрузить историю в context
    history = _load_room_history(room_id, agents)
    for msg in history:
        components["context"].add_message(msg)

    executor = PipelineExecutor(
        room=room,
        chat_service=components["chat_service"],
        strategy=components["strategy"],
        agents=components["agents"],
        on_message=callback,
        max_discuss_rounds=50,
    )

    task = asyncio.create_task(_run_and_cleanup(room_id, executor, text, sender))
    async with _get_pipeline_lock():
        old = _pipeline_tasks.pop(room_id, None)
        if old and not old.done():
            old.cancel()
            try:
                await old
            except asyncio.CancelledError:
                pass
        _pipeline_tasks[room_id] = task
    logger.info("run_pipeline_executor room_id=%s STARTED text_len=%d sender=%s", room_id, len(text), sender)
    return True


async def _run_and_cleanup(room_id: int, executor, text: str, sender: str) -> None:
    """Запуск executor и удаление задачи из _pipeline_tasks по завершении."""
    try:
        await executor.run(text, sender)
    except asyncio.CancelledError:
        logger.info("run_pipeline_executor room_id=%s CANCELLED", room_id)
    finally:
        async with _get_pipeline_lock():
            _pipeline_tasks.pop(room_id, None)


async def cancel_pipeline_task(room_id: int) -> bool:
    """Отменить выполняющийся pipeline для комнаты. Возвращает True если задача была отменена."""
    async with _get_pipeline_lock():
        task = _pipeline_tasks.pop(room_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("cancel_pipeline_task room_id=%s cancelled", room_id)
        return True
    return False


async def enqueue_room_run(room_id: int, text: str, sender: str = "user", room=None) -> bool:
    """
    Триггер оркестрации: запустить pipeline executor.

    Вызывать после сохранения сообщения в БД. Pipeline выполняется в фоне.
    """
    return await run_pipeline_executor(room_id, text, sender, room)
