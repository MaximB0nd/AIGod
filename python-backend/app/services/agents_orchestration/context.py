from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .message import Message
from .message_type import MessageType

@dataclass
class ConversationContext:
    """
    Хранит состояние разговора и общую память для всех стратегий.
    Доступен из любой стратегии и может быть расширен.
    """
    history: List[Message] = field(default_factory=list)
    shared_memory: Dict[str, Any] = field(default_factory=dict)
    current_topic: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message):
        """Добавить сообщение в историю"""
        self.history.append(message)
    
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """Получить последние n сообщений"""
        return self.history[-n:]
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[Message]:
        """Получить сообщения определенного типа"""
        return [msg for msg in self.history if msg.type == msg_type]
    
    def get_messages_by_sender(self, sender: str) -> List[Message]:
        """Получить сообщения от конкретного отправителя"""
        return [msg for msg in self.history if msg.sender == sender]
    
    def get_messages_by_round(self, round_number: int) -> List[Message]:
        """Получить сообщения определенного раунда"""
        return [msg for msg in self.history if msg.round_number == round_number]
    
    def update_memory(self, key: str, value: Any):
        """Сохранить значение в общей памяти"""
        self.shared_memory[key] = value
    
    def get_memory(self, key: str, default=None) -> Any:
        """Получить значение из общей памяти"""
        return self.shared_memory.get(key, default)
    
    def clear_history(self):
        """Очистить историю сообщений"""
        self.history.clear()
    
    def clear_memory(self):
        """Очистить общую память"""
        self.shared_memory.clear()
    
    def get_last_message(self) -> Optional[Message]:
        """Получить последнее сообщение"""
        return self.history[-1] if self.history else None
    
    def get_last_message_by_sender(self, sender: str) -> Optional[Message]:
        """Получить последнее сообщение от конкретного отправителя"""
        for msg in reversed(self.history):
            if msg.sender == sender:
                return msg
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по разговору"""
        stats = {
            "total_messages": len(self.history),
            "participants": len(self.participants),
            "messages_by_type": {},
            "messages_by_sender": {},
            "current_topic": self.current_topic
        }
        
        for msg_type in MessageType:
            count = len(self.get_messages_by_type(msg_type))
            if count > 0:
                stats["messages_by_type"][msg_type.value] = count
        
        for participant in self.participants:
            count = len(self.get_messages_by_sender(participant))
            if count > 0:
                stats["messages_by_sender"][participant] = count
        
        return stats
    
    def export_conversation(self, include_metadata: bool = False) -> str:
        """Экспортировать разговор в текст"""
        lines = []
        for msg in self.history:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            if include_metadata:
                lines.append(f"[{timestamp}] {msg.type}: {msg.sender} -> {msg.content}")
                if msg.metadata:
                    lines.append(f"      metadata: {msg.metadata}")
            else:
                lines.append(f"[{timestamp}] {msg.sender}: {msg.content}")
        return "\n".join(lines)
