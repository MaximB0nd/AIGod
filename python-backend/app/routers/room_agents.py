"""Роуты для агентов в контексте комнаты."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db
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
from app.services.orchestration_background import registry
from app.services.relationship_model_service import get_relationship_manager
from app.utils.mood import get_agent_mood
from app.ws import broadcast_chat_event, broadcast_chat_message, broadcast_graph_edge

# Endpoint для управления агентами, их связями с комнатами и т.д.

router = APIRouter(prefix="/{room_id}", tags=["room-agents"])


def _agent_in_room(room: Room, agent_id: int) -> Agent | None:
    return next((a for a in room.agents if a.id == agent_id), None)


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
    """Полная информация по агенту."""
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден в этой комнате")

    memories = db.query(Memory).filter(Memory.agent_id == agent_id).limit(10).all()
    plans = db.query(Plan).filter(Plan.agent_id == agent_id).all()

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
    """Удалить агента из комнаты."""
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден в этой комнате")

    room.agents.remove(agent)
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
def broadcast_event(
    data: EventBroadcastIn,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(broadcast_chat_event, room.id, payload)

    return EventOut(
        id=str(event.id),
        type=event.type,
        agentIds=event.agent_ids or [],
        description=event.description,
        timestamp=event.created_at.isoformat() if event.created_at else "",
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

    return FeedOut(
        items=[item["data"] for item in items]
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
    agent = _agent_in_room(room, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")

    orchestration_type = getattr(room, "orchestration_type", None) or "single"

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

    if orchestration_type != "single":
        # Режим оркестрации: запускаем в фоне, кладём сообщение в очередь
        client = await registry.get_or_start(room)
        if client:
            await client.send_user_message(data.text)
            payload = {
                "id": str(msg.id),
                "text": msg.text,
                "sender": msg.sender,
                "agentId": str(agent_id),
                "timestamp": msg.created_at.isoformat() if msg.created_at else "",
                "agentResponse": None,
            }
            background_tasks.add_task(broadcast_chat_message, room.id, payload)
            return MessageOut(
                id=str(msg.id),
                text=msg.text,
                sender=msg.sender,
                timestamp=msg.created_at.isoformat() if msg.created_at else "",
                agentId=str(agent_id),
                agentResponse=None,
            )
        # fallback: если оркестрация не создалась (нет Yandex и т.п.), идём в single

    # Режим single — ChatService
    session_id = f"room_{room.id}_agent_{agent_id}"
    agent_response = get_agent_response(agent, session_id, data.text)

    agent_msg = Message(
        room_id=room.id,
        agent_id=agent_id,
        text=agent_response,
        sender=agent.name,
    )
    db.add(agent_msg)
    db.commit()
    db.refresh(agent_msg)

    payload = {
        "id": str(msg.id),
        "text": msg.text,
        "sender": msg.sender,
        "agentId": str(agent_id),
        "timestamp": msg.created_at.isoformat() if msg.created_at else "",
        "agentResponse": agent_response,
    }
    background_tasks.add_task(broadcast_chat_message, room.id, payload)

    return MessageOut(
        id=str(msg.id),
        text=msg.text,
        sender=msg.sender,
        timestamp=msg.created_at.isoformat() if msg.created_at else "",
        agentId=str(agent_id),
        agentResponse=agent_response,
    )
