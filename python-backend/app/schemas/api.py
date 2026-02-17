"""Схемы для API по спецификации."""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class AuthRegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: Optional[str] = None


class AuthLoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    token: str
    refreshToken: str = ""


# --- Rooms ---
OrchestrationTypeLiteral = Literal["single", "circular", "narrator", "full_context"]


class RoomCreateIn(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    orchestration_type: OrchestrationTypeLiteral = Field("single", description="Паттерн взаимодействия агентов")


class RoomUpdateIn(BaseModel):
    """Обновление комнаты. Только описание и/или скорость, оба поля опциональны."""
    description: Optional[str] = None
    speed: Optional[float] = Field(None, ge=0.1, le=10.0)


class RoomOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    speed: float = 1.0
    orchestration_type: str = "single"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    agentCount: Optional[int] = None

    @classmethod
    def from_room(cls, room, agent_count: int | None = None):
        return cls(
            id=str(room.id),
            name=room.name,
            description=room.description,
            speed=float(room.speed or 1.0),
            orchestration_type=getattr(room, "orchestration_type", None) or "single",
            createdAt=room.created_at.isoformat() if room.created_at else None,
            updatedAt=room.updated_at.isoformat() if getattr(room, "updated_at", None) else None,
            agentCount=agent_count if agent_count is not None else (len(room.agents) if hasattr(room, "agents") else None),
        )


class RoomsListOut(BaseModel):
    rooms: list[RoomOut]


# --- Agents ---
class MoodOut(BaseModel):
    mood: str
    level: float
    icon: Optional[str] = None
    color: Optional[str] = None


class AgentSummaryOut(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    mood: MoodOut


class AgentCreateIn(BaseModel):
    name: str = Field(..., min_length=1)
    character: str = Field("", min_length=0)  # опционально при agentId
    avatar: Optional[str] = None
    agentId: Optional[int] = None  # если указан — добавить существующего агента в комнату


class AgentFullOut(AgentSummaryOut):
    character: str
    keyMemories: list[dict] = []
    plans: list[dict] = []


class AgentsListOut(BaseModel):
    agents: list[AgentSummaryOut]


# --- Memories, Plans ---
class MemoryOut(BaseModel):
    id: str
    content: str
    timestamp: str
    importance: Optional[float] = None


class MemoriesListOut(BaseModel):
    memories: list[MemoryOut]
    total: int


class PlanOut(BaseModel):
    id: str
    description: str
    status: Literal["pending", "in_progress", "done"]


class PlansListOut(BaseModel):
    plans: list[PlanOut]


# --- Relationships ---
class RelationshipUpdateIn(BaseModel):
    """Обновление ребра графа: agent1_id < agent2_id для упорядоченности."""
    agent1Id: int
    agent2Id: int
    sympathyLevel: float = Field(..., ge=-1.0, le=1.0)


class RelationshipNodeOut(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    mood: MoodOut


class RelationshipEdgeOut(BaseModel):
    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    agentName: Optional[str] = None
    sympathyLevel: float

    model_config = {"populate_by_name": True}


class RelationshipsOut(BaseModel):
    nodes: list[RelationshipNodeOut]
    edges: list[RelationshipEdgeOut]


# --- Events ---
class EventCreateIn(BaseModel):
    description: str
    type: str = "user_event"
    agentIds: list[str] = []


class EventOut(BaseModel):
    id: str
    type: str
    agentIds: list[str]
    description: str
    timestamp: str


class EventBroadcastIn(BaseModel):
    description: str
    type: str = "user_event"


# --- Messages ---
class MessageCreateIn(BaseModel):
    text: str = Field(..., min_length=1)
    sender: str = "user"


class MessageOut(BaseModel):
    id: str
    text: str
    sender: str
    timestamp: str
    agentId: Optional[str] = None
    agentResponse: Optional[str] = None


# --- Feed ---
class FeedEventItem(BaseModel):
    type: Literal["event"] = "event"
    id: str
    eventType: str
    agentIds: list[str]
    description: str
    timestamp: str


class FeedMessageItem(BaseModel):
    type: Literal["message"] = "message"
    id: str
    text: str
    sender: str
    agentId: Optional[str] = None
    timestamp: str


class FeedOut(BaseModel):
    items: list[FeedEventItem | FeedMessageItem]


# --- Speed ---
class SpeedUpdateIn(BaseModel):
    speed: float = Field(..., ge=0.1, le=10.0)


class SpeedOut(BaseModel):
    speed: float


# --- Success ---
class SuccessOut(BaseModel):
    success: bool = True
