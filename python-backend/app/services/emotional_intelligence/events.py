"""
События для эмоционального интеллекта
"""
from enum import Enum
from typing import Dict, Any
from datetime import datetime

class EventType(str, Enum):
    """Типы событий"""
    ENTITY_ADDED = "entity_added"
    EMOTION_UPDATED = "emotion_updated"
    ANALYSIS_COMPLETED = "analysis_completed"
    THRESHOLD_REACHED = "threshold_reached"
    MOOD_CHANGED = "mood_changed"
    EMOTIONAL_CONTAGION = "emotional_contagion"

class EmotionalEvent:
    """Событие в системе эмоционального интеллекта"""
    
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
            "
