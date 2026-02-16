from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RoomBase(BaseModel):
    name: str = Field(..., min_length=1)


class RoomCreate(RoomBase):
    agent_ids: list[int] = Field(default_factory=list, description="ID агентов для добавления в комнату")


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    agent_ids: Optional[list[int]] = None


class AgentBrief(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class RoomOut(RoomBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    agents: list[AgentBrief] = []

    model_config = {"from_attributes": True}
