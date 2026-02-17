"""Общие схемы по спецификации API."""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# Mood
class MoodOut(BaseModel):
    mood: str
    level: float
    icon: Optional[str] = None
    color: Optional[str] = None


# Agent
class AgentSummaryOut(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    mood: MoodOut


# Memory, Plan
class MemoryOut(BaseModel):
    id: str
    content: str
    timestamp: str
    importance: Optional[float] = None


class PlanOut(BaseModel):
    id: str
    description: str
    status: Literal["pending", "in_progress", "done"]


# Relationship
class RelationshipEdgeOut(BaseModel):
    from_: str = Field(alias="from")
    to: str
    agentName: Optional[str] = None
    sympathyLevel: float
