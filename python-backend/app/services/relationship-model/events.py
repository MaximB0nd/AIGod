"""
Система событий для отношений
"""
from enum import Enum
from typing import Dict, Any
from datetime import datetime

class EventType(str, Enum):
    """Типы событий"""
    RELATIONSHIP_UPDATED = "relationship_updated"
    PARTICIPANT_ADDED = "participant_added"
    PARTICIPANT_REMOVED = "participant_removed"
    ANALYSIS_COMPLETED = "analysis_completed"
    THRESHOLD_REACHED = "threshold_reached"
    NETWORK_CHANGED = "network_changed"

class RelationshipEvent:
    """Событие в системе отношений"""
    
    def __init__(self, 
                 type: EventType,
                 data: Dict[str, Any],
                 source: str = "system"):
        self.type = type
        self.data = data
        self.source = source
        self.timestamp = datetime.now()
        self.id = f"{type.value}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data
        }

class EventEmitter:
    """Эмиттер событий"""
    
    def __init__(self):
        self._handlers = {}
        self._history = []
    
    def on(self, event_type: EventType, handler):
        """Подписаться на событие"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def emit(self, event: RelationshipEvent):
        """Испустить событие"""
        # Сохраняем в историю
        self._history.append(event)
        
        # Вызываем обработчики
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Получить историю событий"""
        return [e.to_dict() for e in self._history[-limit:]]
