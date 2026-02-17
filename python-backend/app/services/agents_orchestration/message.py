from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from .message_type import MessageType

@dataclass
class Message:
    content: str
    type: MessageType
    sender: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    target_agent: Optional[str] = None
    round_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "type": self.type.value,
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "target_agent": self.target_agent,
            "round_number": self.round_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            content=data["content"],
            type=MessageType(data["type"]),
            sender=data["sender"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            target_agent=data.get("target_agent"),
            round_number=data.get("round_number", 0)
        )
    
    def __str__(self) -> str:
        return f"[{self.type}] {self.sender}: {self.content[:50]}..."
