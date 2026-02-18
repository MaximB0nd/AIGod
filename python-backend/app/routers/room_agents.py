"""Роуты для агентов в контексте комнаты."""
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

logger = logging.getLogger("aigod.room_agents")
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db, SessionLocal
from app.dependencies import get_current_user, get_room_for_user
from app.models.agent import Agent
from app.models.event import Event
from app.models.memory import Memory
from app.models.message import Message
from app.models.plan import Plan
from app.models.relationship import Relationship
from app.models.room import Room
from app.models.user import User
from app.schemas.api import (
    AgentCreateIn,
    RelationshipUpdateIn,
    AgentFullOut,
    AgentSummaryOut,
    AgentsListOut,
    EventBroadcastIn,
    EventCreateIn,
    EventOut,
    FeedOut,
    MessageItemOut,
    MessagesListOut,
    MemoriesListOut,
    MemoryOut,
    MessageCreateIn,
    MessageOut,
    PlansListOut,
    PlanOut,
    RelationshipsOut,
    SpeedUpdateIn,
    SuccessOut,
)
from app.services.llm_service import get_agent_response
from app.services.orchestration_background import enqueue_room_run, registry
from app.services.relationship_model_service import get_relationship_manager
from app.services.room_services_registry import (
    get_emotional_integration,
    get_memory_integration,
    ensure_emotional_agents_registered,
)
from app.utils.mood import get_agent_mood
from app.ws import broadcast_chat_event, broadcast_chat_message, broadcast_graph_edge

# Endpoint для управления агентами, их связями с комнатами и т.д.

router = APIRouter(prefix="/{room_id}", tags=["room-agents"])


def _agent_in_room(room: Room, agent_id: int) -> Agent | None:
    return next((a for a in room.agents if a.id == agent_id), None)


def _write_agent_memory_to_sql(
    db: Session, room_id: int, agent_id: int | None, agent_name: str, content: str, importance: float = 0.6
) -> None:
    """Записать воспоминание агента в SQL-таблицу Memory (для API keyMemories)."""
    if agent_id is None or not content or not content.strip():
        return
    try:
        m = Memory(
            agent_id=agent_id,
            room_id=room_id,
            content=content[:2000] if len(content) > 2000 else content,
            importance=importance,
        )
        db.add(m)
        db.commit()
    except Exception as e:
        logger.warning("_write_agent_memory_to_sql failed: %s", e)
        db.rollback()


def _update_room_services_on_message(
    room_id: int,
    agents: list,
    user_text: str,
    user_sender: str,
    agent_response: str,
    agent_name: str,
) -> None:
    """Фоновая задача: обновить память и эмоции после обмена сообщениями."""
    db = SessionLocal()
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            return
        db.refresh(room)
        agent_names = [a.name for a in room.agents]
        conv_id = f"room_{room_id}"

        # Память (context_memory)
        mem = get_memory_integration(room)
        if mem:
            try:
                asyncio.run(mem.on_user_message(user_text, conv_id, agent_names))
                asyncio.run(
                    mem.on_agent_message(
                        agent_response, agent_name, conv_id,
                        metadata={"room_id": room_id},
                    )
                )
            except Exception as e:
                logger.warning("Memory update failed: %s", e)

        # SQL Memory — мост для API keyMemories
        agent_obj = next((a for a in room.agents if a.name == agent_name), None)
        if agent_obj and agent_response:
            _write_agent_memory_to_sql(db, room_id, agent_obj.id, agent_name, agent_response, importance=0.6)

        # Эмоции
        emo = get_emotional_integration(room)
        if emo:
            ensure_emotional_agents_registered(room, emo)
    finally:
        db.close()


def _agent_summary(agent: Agent) -> AgentSummaryOut:
    mood = get_agent_mood(agent.state_vector)
    return AgentSummaryOut(
        id=str(agent.id),
        name=agent.name,
        avatar=agent.avatar_url,
        mood=mood,
    )


@router.get("/agents", response_model=AgentsListOut)
def get_room_agents(room: Room = Depends(get_room_for_user)):
    """Получить всех агентов комнаты."""
    return AgentsListOut(
        agents=[_agent_summary(a) for a in room.agents]
    )


@router.get("/agents/{agent_id}", response_model=AgentFullOut)
def get_room_agent(
    agent_id: int,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Полная информация по агенту: характер, воспоминания, планы, взаимоотношения."""
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден в этой комнате")

    memories = db.query(Memory).filter(Memory.agent_id == agent_id).limit(10).all()
    plans = db.query(Plan).filter(Plan.agent_id == agent_id).all()

    # Взаимоотношения: ребра, где agent_id участвует как agent1 или agent2
    room_agent_ids = {a.id for a in room.agents}
    rels = db.query(Relationship).filter(
        Relationship.room_id == room.id,
        (Relationship.agent1_id == agent_id) | (Relationship.agent2_id == agent_id),
    ).all()
    relationships = []
    for r in rels:
        other_id = r.agent2_id if r.agent1_id == agent_id else r.agent1_id
        if other_id in room_agent_ids:
            other_agent = next((a for a in room.agents if a.id == other_id), None)
            relationships.append({
                "agentId": str(other_id),
                "agentName": other_agent.name if other_agent else str(other_id),
                "sympathyLevel": r.sympathy_value,
            })

    return AgentFullOut(
        id=str(agent.id),
        name=agent.name,
        avatar=agent.avatar_url,
        mood=get_agent_mood(agent.state_vector),
        character=agent.personality,
        keyMemories=[
            {
                "id": str(m.id),
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else "",
                "importance": m.importance,
            }
            for m in memories
        ],
        plans=[
            {"id": str(p.id), "description": p.description, "status": p.status}
            for p in plans
        ],
        relationships=relationships,
    )


@router.post("/agents", response_model=AgentSummaryOut)
def create_agent(
    data: AgentCreateIn,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать агента и добавить в комнату, или добавить существующего по agentId."""
    if data.agentId:
        # Добавить существующего агента
        agent = db.query(Agent).filter(Agent.id == data.agentId).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Агент не найден")
        if agent in room.agents:
            raise HTTPException(status_code=400, detail="Агент уже в комнате")
        room.agents.append(agent)
        db.commit()
        db.refresh(agent)
        return _agent_summary(agent)

    # Создать нового
    if any(a.name == data.name for a in room.agents):
        raise HTTPException(status_code=400, detail="Агент с таким именем уже в комнате")

    agent = Agent(
        name=data.name,
        personality=data.character or "Персонаж",
        avatar_url=data.avatar,
        state_vector={"mood": "neutral", "mood_level": 0.5},
        user_id=current_user.id,
    )
    db.add(agent)
    db.flush()
    room.agents.append(agent)
    db.commit()
    db.refresh(agent)
    return _agent_summary(agent)


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(
    agent_id: int,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Удалить агента из комнаты. Ссылки в сообщениях становятся NULL. Нельзя удалить Рассказчика в комнате narrator."""
    from app.constants import NARRATOR_AGENT_NAME

    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден в этой комнате")

    ot = getattr(room, "orchestration_type", None) or "single"
    if ot == "narrator" and agent.name == NARRATOR_AGENT_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить Рассказчика из комнаты со стратегией narrator",
        )

    # Все ссылки в сообщениях на этого агента устанавливаем в NULL
    db.query(Message).filter(Message.agent_id == agent_id).update(
        {Message.agent_id: None}, synchronize_session=False
    )
    db.delete(agent)
    db.commit()


@router.get("/agents/{agent_id}/memories", response_model=MemoriesListOut)
def get_agent_memories(
    agent_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Воспоминания агента. Заглушка: полная версия с векторной БД будет позже."""
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    # Заглушка — возвращаем пустой список с сообщением
    memories_q = db.query(Memory).filter(Memory.agent_id == agent_id, Memory.room_id == room.id)
    total = memories_q.count()
    items = memories_q.order_by(Memory.created_at.desc()).offset(offset).limit(limit).all()

    return MemoriesListOut(
        memories=[
            MemoryOut(
                id=str(m.id),
                content=m.content,
                timestamp=m.created_at.isoformat() if m.created_at else "",
                importance=m.importance,
            )
            for m in items
        ],
        total=total,
    )


@router.get("/agents/{agent_id}/plans", response_model=PlansListOut)
def get_agent_plans(
    agent_id: int,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Планы агента. Заглушка."""
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    plans = db.query(Plan).filter(Plan.agent_id == agent_id).all()
    return PlansListOut(
        plans=[
            PlanOut(id=str(p.id), description=p.description, status=p.status)
            for p in plans
        ]
    )


@router.patch("/relationships")
def update_relationship(
    data: RelationshipUpdateIn,
    background_tasks: BackgroundTasks,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """
    Обновить ребро графа отношений.
    agent1Id, agent2Id — id агентов в комнате. sympathyLevel: -1 .. 1.
    Рассылает обновление в WebSocket графа.
    """
    a1, a2 = data.agent1Id, data.agent2Id
    if a1 == a2:
        raise HTTPException(status_code=400, detail="agent1Id и agent2Id должны отличаться")

    room_agent_ids = [a.id for a in room.agents]
    if a1 not in room_agent_ids or a2 not in room_agent_ids:
        raise HTTPException(status_code=400, detail="Оба агента должны быть в комнате")

    # Упорядочиваем пару (agent1 < agent2) для совместимости с БД
    if a1 > a2:
        a1, a2 = a2, a1

    rel = db.query(Relationship).filter(
        Relationship.room_id == room.id,
        Relationship.agent1_id == a1,
        Relationship.agent2_id == a2,
    ).first()
    if rel:
        rel.sympathy_value = data.sympathyLevel
    else:
        rel = Relationship(
            room_id=room.id,
            agent1_id=a1,
            agent2_id=a2,
            sympathy_value=data.sympathyLevel,
        )
        db.add(rel)
    db.commit()

    # Рассылка в WebSocket графа
    background_tasks.add_task(
        broadcast_graph_edge,
        room.id,
        str(a1),
        str(a2),
        data.sympathyLevel,
    )

    return {
        "from": str(a1),
        "to": str(a2),
        "sympathyLevel": data.sympathyLevel,
    }


@router.get("/relationships", response_model=RelationshipsOut)
def get_relationships(
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Взаимоотношения агентов комнаты."""
    nodes = [
        {
            "id": str(a.id),
            "name": a.name,
            "avatar": a.avatar_url,
            "mood": get_agent_mood(a.state_vector),
        }
        for a in room.agents
    ]
    rels = db.query(Relationship).filter(Relationship.room_id == room.id).all()
    edges = []
    for r in rels:
        if r.agent1_id in [a.id for a in room.agents] and r.agent2_id in [a.id for a in room.agents]:
            agent_name = next((a.name for a in room.agents if a.id == r.agent2_id), None)
            edges.append({
                "from": str(r.agent1_id),
                "to": str(r.agent2_id),
                "agentName": agent_name,
                "sympathyLevel": r.sympathy_value,
            })
    return RelationshipsOut(nodes=nodes, edges=edges)


@router.get("/relationship-model")
def get_relationship_model(
    room: Room = Depends(get_room_for_user),
):
    """
    Данные об отношениях между агентами из модуля relationship-model.

    Включает граф с типами отношений (friendly, hostile и т.д.), историю изменений
    и сетевую статистику.
    """
    manager = get_relationship_manager(room)
    state = manager.get_full_state()

    # Добавляем маппинг name -> agent_id для фронтенда
    name_to_id = {a.name: str(a.id) for a in room.agents}
    state["agent_ids"] = name_to_id

    return state


@router.get("/emotional-state")
def get_emotional_state(room: Room = Depends(get_room_for_user)):
    """Эмоциональное состояние агентов комнаты (модуль emotional_intelligence)."""
    integration = get_emotional_integration(room)
    if not integration:
        return {"agents": {}, "message": "Emotional service unavailable"}
    ensure_emotional_agents_registered(room, integration)
    states = integration.get_all_emotional_states()
    name_to_id = {a.name: str(a.id) for a in room.agents}
    return {"agent_ids": name_to_id, "states": states}


@router.get("/context-memory")
def get_context_memory(
    room: Room = Depends(get_room_for_user),
    query: str = Query("", description="Поиск по контексту"),
):
    """Контекст разговора комнаты (модуль context_memory)."""
    integration = get_memory_integration(room)
    if not integration:
        return {"context": "", "message": "Memory service unavailable"}
    try:
        summary = integration.get_conversation_summary()
        return {"summary": summary or "", "stats": integration.get_stats()}
    except Exception as e:
        return {"context": "", "error": str(e)}


@router.post("/orchestration/start")
async def start_orchestration(room: Room = Depends(get_room_for_user)):
    """
    Подготовка оркестрации. С pipeline executor оркестрация запускается при каждом сообщении.
    Проверяет, что компоненты (chat_service, strategy) создаются успешно.
    """
    from app.services.orchestration_service import create_pipeline_components

    orchestration_type = getattr(room, "orchestration_type", None) or "single"
    if orchestration_type == "single":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Оркестрация недоступна для комнаты с orchestration_type=single",
        )
    if not room.agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Добавьте агентов в комнату перед запуском оркестрации",
        )
    components = create_pipeline_components(room)
    if components:
        return {"status": "ready", "roomId": room.id, "orchestration_type": orchestration_type}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Не удалось создать компоненты оркестрации",
    )


@router.post("/orchestration/stop")
async def stop_orchestration(room: Room = Depends(get_room_for_user)):
    """
    Остановить оркестрацию: отменить выполняющийся pipeline и long-running клиент (если есть).
    """
    from app.services.orchestration_background import cancel_pipeline_task

    cancelled = await cancel_pipeline_task(room.id)
    await registry.stop_room(room.id)
    return {"status": "stopped", "roomId": room.id, "pipelineCancelled": cancelled}


@router.post("/events", response_model=EventOut)
def create_event(
    data: EventCreateIn,
    background_tasks: BackgroundTasks,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Создать событие в комнате."""
    room_agent_ids = [a.id for a in room.agents]
    agent_ids_int = []
    for aid in data.agentIds:
        try:
            i = int(aid) if isinstance(aid, str) else aid
            if i in room_agent_ids:
                agent_ids_int.append(i)
        except (ValueError, TypeError):
            pass
    agent_ids_str = [str(a) for a in agent_ids_int] if agent_ids_int else [str(a.id) for a in room.agents]

    event = Event(
        room_id=room.id,
        type=data.type,
        description=data.description,
        agent_ids=agent_ids_str,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Рассылка в WebSocket чата
    payload = {
        "id": str(event.id),
        "eventType": event.type,
        "agentIds": event.agent_ids or [],
        "description": event.description,
        "timestamp": event.created_at.isoformat() if event.created_at else "",
    }
    background_tasks.add_task(broadcast_chat_event, room.id, payload)

    return EventOut(
        id=str(event.id),
        type=event.type,
        agentIds=event.agent_ids or [],
        description=event.description,
        timestamp=event.created_at.isoformat() if event.created_at else "",
    )


@router.post("/events/broadcast", response_model=EventOut)
async def broadcast_event(
    data: EventBroadcastIn,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Событие для всех агентов комнаты."""
    agent_ids = [str(a.id) for a in room.agents]
    event = Event(
        room_id=room.id,
        type=data.type,
        description=data.description,
        agent_ids=agent_ids,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    payload = {
        "id": str(event.id),
        "eventType": event.type,
        "agentIds": event.agent_ids or [],
        "description": event.description,
        "timestamp": event.created_at.isoformat() if event.created_at else "",
    }
    await broadcast_chat_event(room.id, payload)

    # Если type="user_message" или "chat" — сообщение пользователя в чат, триггерим агентов
    if data.type in ("user_message", "chat") and room.agents:
        msg = Message(room_id=room.id, agent_id=None, text=data.description, sender="user")
        db.add(msg)
        db.commit()
        db.refresh(msg)
        payload_user = {
            "id": str(msg.id),
            "text": msg.text,
            "sender": msg.sender,
            "agentId": None,
            "timestamp": msg.created_at.isoformat() if msg.created_at else "",
            "agentResponse": None,
        }
        await broadcast_chat_message(room.id, payload_user)
        enqueued = await enqueue_room_run(room.id, data.description, "user", room=room)
        if enqueued:
            logger.info("events/broadcast user_message: оркестрация room_id=%s", room.id)
        else:
            for agent in room.agents:
                asyncio.create_task(
                    _generate_agent_reply_async(
                        room.id, agent.id, agent.name, data.description, "user"
                    )
                )
            logger.info("events/broadcast user_message: триггер %d агентов room_id=%s", len(room.agents), room.id)

    return EventOut(
        id=str(event.id),
        type=event.type,
        agentIds=event.agent_ids or [],
        description=event.description,
        timestamp=event.created_at.isoformat() if event.created_at else "",
    )


async def _generate_agent_reply_async(
    room_id: int,
    agent_id: int,
    agent_name: str,
    user_text: str,
    user_sender: str,
) -> None:
    """
    Фоновая задача: сгенерировать ответ агента на сообщение в комнату.
    Вызывается для каждого агента при POST /messages (общий чат комнаты).
    """
    logger.info("_generate_agent_reply START room_id=%s agent_id=%s agent_name=%s", room_id, agent_id, agent_name)
    db = SessionLocal()
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            logger.warning("_generate_agent_reply room_id=%s room not found", room_id)
            return
        agent = _agent_in_room(room, agent_id)
        if not agent:
            logger.warning("_generate_agent_reply room_id=%s agent_id=%s not in room", room_id, agent_id)
            return
        session_id = f"room_{room_id}_agent_{agent_id}"
        logger.info("_generate_agent_reply LLM call room_id=%s agent=%s session=%s", room_id, agent_name, session_id)
        loop = asyncio.get_event_loop()
        agent_response = await loop.run_in_executor(
            None,
            lambda: get_agent_response(agent, session_id, user_text, room=room),
        )
        agent_msg = Message(
            room_id=room_id,
            agent_id=agent_id,
            text=agent_response or "",
            sender=agent_name,
        )
        db.add(agent_msg)
        db.commit()
        db.refresh(agent_msg)
        logger.info("_generate_agent_reply saved msg_id=%s room_id=%s agent=%s response_len=%d", agent_msg.id, room_id, agent_name, len(agent_response or ""))
        payload = {
            "id": str(agent_msg.id),
            "text": agent_msg.text,
            "sender": agent_name,
            "agentId": str(agent_id),
            "timestamp": agent_msg.created_at.isoformat() if agent_msg.created_at else "",
            "agentResponse": None,
        }
        await broadcast_chat_message(room_id, payload)
        logger.info("_generate_agent_reply DONE room_id=%s agent=%s broadcast OK", room_id, agent_name)
        # Обновление памяти/эмоций — sync, запускаем в executor чтобы не блокировать
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _update_room_services_on_message(
                room_id, list(room.agents), user_text, user_sender, agent_msg.text, agent_name
            ),
        )
    except Exception as e:
        logger.exception("Ошибка _generate_agent_reply room_id=%s agent_id=%s: %s", room_id, agent_id, e)
    finally:
        db.close()


@router.post("/messages", response_model=MessageOut)
async def send_room_message(
    data: MessageCreateIn,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """
    Отправить сообщение в общий чат комнаты.

    Сообщение видно всем агентам. Ответят все агенты в комнате (в режиме single)
    или оркестрация (circular, narrator, full_context).

    Для личной переписки с конкретным агентом используйте
    POST /api/rooms/{roomId}/agents/{agentId}/messages.
    """
    if not room.agents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Добавьте агентов в комнату перед отправкой сообщений",
        )

    # Сохраняем сообщение пользователя в комнату (agent_id=None — не конкретному агенту)
    msg = Message(
        room_id=room.id,
        agent_id=None,
        text=data.text,
        sender=data.sender,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    logger.info("Сообщение комнаты сохранено msg_id=%s room_id=%s", msg.id, room.id)

    payload_user = {
        "id": str(msg.id),
        "text": msg.text,
        "sender": msg.sender,
        "agentId": None,
        "timestamp": msg.created_at.isoformat() if msg.created_at else "",
        "agentResponse": None,
    }
    await broadcast_chat_message(room.id, payload_user)

    orchestration_type = getattr(room, "orchestration_type", None) or "single"

    if orchestration_type != "single":
        enqueued = await enqueue_room_run(room.id, data.text, data.sender, room=room)
        if enqueued:
            logger.info("Оркестрация: enqueue_room_run room_id=%s — сообщение в очереди", room.id)
            return MessageOut(
                id=str(msg.id),
                text=msg.text,
                sender=msg.sender,
                timestamp=msg.created_at.isoformat() if msg.created_at else "",
                agentId=None,
                agentResponse=None,
            )
        logger.warning("Оркестрация не создана (Yandex?), fallback: триггер всех агентов")

    # Режим single (или fallback): триггерим ответ от каждого агента
    for agent in room.agents:
        asyncio.create_task(
            _generate_agent_reply_async(
                room.id,
                agent.id,
                agent.name,
                data.text,
                data.sender,
            )
        )
    logger.info("Триггер ответов от %d агентов room_id=%s", len(room.agents), room.id)

    return MessageOut(
        id=str(msg.id),
        text=msg.text,
        sender=msg.sender,
        timestamp=msg.created_at.isoformat() if msg.created_at else "",
        agentId=None,
        agentResponse=None,
    )


@router.get("/messages", response_model=MessagesListOut)
def get_messages(
    after_id: int | None = Query(None, description="Загрузить сообщения старше этого id"),
    limit: int = Query(20, ge=1, le=100),
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """
    Сообщения комнаты для ленивой загрузки.

    Если after_id указан — возвращает до limit сообщений с id < after_id (более старые).
    Иначе — последние limit сообщений.
    hasMore=true, если есть ещё сообщения для подгрузки.
    """
    q = db.query(Message).filter(Message.room_id == room.id)
    if after_id is not None:
        q = q.filter(Message.id < after_id)
    q = q.order_by(Message.created_at.desc())
    messages = q.limit(limit + 1).all()  # +1 чтобы проверить hasMore
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]
    logger.info("GET /messages room_id=%s after_id=%s limit=%s → %d сообщений hasMore=%s", room.id, after_id, limit, len(messages), has_more)
    return MessagesListOut(
        messages=[
            MessageItemOut(
                id=str(m.id),
                text=m.text,
                sender=m.sender,
                agentId=str(m.agent_id) if m.agent_id else None,
                timestamp=m.created_at.isoformat() if m.created_at else "",
            )
            for m in messages
        ],
        hasMore=has_more,
    )


@router.get("/feed", response_model=FeedOut)
def get_feed(
    limit: int = Query(20, ge=1, le=100),
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Лента: сообщения и события в хронологическом порядке."""
    events = db.query(Event).filter(Event.room_id == room.id).order_by(Event.created_at.desc()).limit(limit // 2 + 5).all()
    messages = db.query(Message).filter(Message.room_id == room.id).order_by(Message.created_at.desc()).limit(limit // 2 + 5).all()

    items = []
    for e in events:
        items.append({
            "timestamp": e.created_at,
            "sort_key": 1,
            "data": {
                "type": "event",
                "id": str(e.id),
                "eventType": e.type,
                "agentIds": e.agent_ids or [],
                "description": e.description,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
            },
        })
    for m in messages:
        items.append({
            "timestamp": m.created_at,
            "sort_key": 0,
            "data": {
                "type": "message",
                "id": str(m.id),
                "text": m.text,
                "sender": m.sender,
                "agentId": str(m.agent_id) if m.agent_id else None,
                "timestamp": m.created_at.isoformat() if m.created_at else "",
            },
        })
    items.sort(key=lambda x: (x["timestamp"] or 0), reverse=True)
    items = items[:limit]

    out_items = [item["data"] for item in items]
    n_events = sum(1 for d in out_items if d.get("type") == "event")
    n_msgs = sum(1 for d in out_items if d.get("type") == "message")
    logger.info("GET /feed room_id=%s limit=%s → %d items (events=%d messages=%d)", room.id, limit, len(out_items), n_events, n_msgs)
    return FeedOut(
        items=out_items
    )


@router.patch("/speed", response_model=dict)
def update_speed(
    data: SpeedUpdateIn,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Изменить скорость симуляции комнаты."""
    room.speed = data.speed
    db.commit()
    return {"speed": room.speed}


@router.post("/agents/{agent_id}/messages", response_model=MessageOut)
async def send_message(
    agent_id: int,
    data: MessageCreateIn,
    background_tasks: BackgroundTasks,
    room: Room = Depends(get_room_for_user),
    db: Session = Depends(get_db),
):
    """Отправить сообщение агенту и получить ответ от LLM."""
    logger.info("POST /agents/%s/messages room_id=%s text_len=%d sender=%s", agent_id, room.id, len(data.text), data.sender)
    agent = _agent_in_room(room, agent_id)
    if not agent:
        logger.warning("Агент agent_id=%s не найден в комнате room_id=%s", agent_id, room.id)
        raise HTTPException(status_code=404, detail="Агент не найден")

    orchestration_type = getattr(room, "orchestration_type", None) or "single"
    logger.info("orchestration_type=%s", orchestration_type)

    # Сохраняем сообщение пользователя
    msg = Message(
        room_id=room.id,
        agent_id=agent_id,
        text=data.text,
        sender=data.sender,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    logger.info("Сообщение пользователя сохранено msg_id=%s", msg.id)

    if orchestration_type != "single":
        enqueued = await enqueue_room_run(room.id, data.text, data.sender, room=room)
        if enqueued:
            logger.info("Оркестрация: enqueue_room_run room_id=%s (POST /agents/{id}/messages)", room.id)
            payload = {
                "id": str(msg.id),
                "text": msg.text,
                "sender": msg.sender,
                "agentId": str(agent_id),
                "timestamp": msg.created_at.isoformat() if msg.created_at else "",
                "agentResponse": None,
            }
            logger.info("Оркестрация: broadcast user msg id=%s", msg.id)
            await broadcast_chat_message(room.id, payload)
            return MessageOut(
                id=str(msg.id),
                text=msg.text,
                sender=msg.sender,
                timestamp=msg.created_at.isoformat() if msg.created_at else "",
                agentId=str(agent_id),
                agentResponse=None,
            )
        logger.warning("Оркестрация: client не создан, fallback на single")
        # fallback: если оркестрация не создалась (нет Yandex и т.п.), идём в single

    # Режим single — ChatService (с обогащением промпта отношениями)
    session_id = f"room_{room.id}_agent_{agent_id}"
    logger.info("LLM запрос session_id=%s agent=%s", session_id, agent.name)
    agent_response = get_agent_response(agent, session_id, data.text, room=room)
    logger.info("LLM ответ получен len=%d: %.80s...", len(agent_response), agent_response[:80] if agent_response else "")

    agent_msg = Message(
        room_id=room.id,
        agent_id=agent_id,
        text=agent_response,
        sender=agent.name,
    )
    db.add(agent_msg)
    db.commit()
    db.refresh(agent_msg)
    logger.info("Сообщение агента сохранено agent_msg_id=%s", agent_msg.id)

    # Сообщение пользователя (с ответом агента в agentResponse)
    payload_user = {
        "id": str(msg.id),
        "text": msg.text,
        "sender": msg.sender,
        "agentId": str(agent_id),
        "timestamp": msg.created_at.isoformat() if msg.created_at else "",
        "agentResponse": agent_response,
    }
    logger.info("Broadcast user msg id=%s agentResponse_len=%d", payload_user["id"], len(agent_response) if agent_response else 0)
    await broadcast_chat_message(room.id, payload_user)

    # Отдельное событие для сообщения агента (чтобы фронт мог показать два пузыря)
    payload_agent = {
        "id": str(agent_msg.id),
        "text": agent_response,
        "sender": agent.name,
        "agentId": str(agent_id),
        "timestamp": agent_msg.created_at.isoformat() if agent_msg.created_at else "",
        "agentResponse": None,
    }
    await broadcast_chat_message(room.id, payload_agent)

    # Обновить память и эмоции в фоне
    background_tasks.add_task(
        _update_room_services_on_message,
        room.id,
        room.agents,
        data.text,
        data.sender,
        agent_response,
        agent.name,
    )

    return MessageOut(
        id=str(msg.id),
        text=msg.text,
        sender=msg.sender,
        timestamp=msg.created_at.isoformat() if msg.created_at else "",
        agentId=str(agent_id),
        agentResponse=agent_response,
    )
