"""Типизированные схемы сообщений WebSocket."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Чат (сообщения и события) ---

class ChatMessagePayload(BaseModel):
    """Сообщение в чате комнаты."""
    id: str
    text: str
    sender: Literal["user", "agent", "system"]
    agentId: Optional[str] = None
    timestamp: str
    agentResponse: Optional[str] = None


class ChatEventPayload(BaseModel):
    """Событие в комнате (взаимодействие агентов, системное)."""
    id: str
    eventType: str
    agentIds: list[str]
    description: str
    timestamp: str
    moodImpact: Optional[dict[str, float]] = None


class ChatWsMessage(BaseModel):
    """Обёртка исходящего сообщения чата."""
    type: Literal["message", "event", "error", "pong"]
    payload: dict


# --- Граф отношений ---

class GraphEdgePayload(BaseModel):
    """Обновление одного ребра в графе отношений."""
    roomId: str
    from_: str = Field(alias="from")
    to: str
    sympathyLevel: float  # -1.0 .. 1.0

    model_config = {"populate_by_name": True}


class GraphWsMessage(BaseModel):
    """Обёртка исходящего сообщения графа."""
    type: Literal["edge_update", "error", "pong"]
    payload: dict
