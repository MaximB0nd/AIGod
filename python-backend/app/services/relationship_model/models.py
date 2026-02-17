from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import json

class RelationshipType(str, Enum):
    """Тип отношений"""
    FRIENDLY = "friendly"      # дружеские (0.5 до 1.0)
    TRUSTING = "trusting"      # доверительные (0.2 до 0.5)
    NEUTRAL = "neutral"        # нейтральные (-0.2 до 0.2)
    SUSPICIOUS = "suspicious"  # подозрительные (-0.5 до -0.2)
    HOSTILE = "hostile"        # враждебные (-1.0 до -0.5)
    
    @classmethod
    def from_value(cls, value: float) -> "RelationshipType":
        if value >= 0.5:
            return cls.FRIENDLY
        elif value >= 0.2:
            return cls.TRUSTING
        elif value >= -0.2:
            return cls.NEUTRAL
        elif value >= -0.5:
            return cls.SUSPICIOUS
        else:
            return cls.HOSTILE

@dataclass
class Relationship:
    """Отношения между двумя сущностями"""
    from_entity: str      # от кого
    to_entity: str        # к кому
    value: float = 0.0    # от -1 до 1
    history: List[Dict] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, delta: float, reason: str = "", source: str = "system"):
        """Обновить значение отношений"""
        old_value = self.value
        self.value = max(-1.0, min(1.0, self.value + delta))
        self.last_updated = datetime.now()
        
        # Сохраняем в историю
        self.history.append({
            "timestamp": self.last_updated.isoformat(),
            "old_value": old_value,
            "new_value": self.value,
            "delta": delta,
            "reason": reason,
            "source": source
        })
        
        # Ограничиваем историю
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return self.value - old_value
    
    def get_type(self) -> RelationshipType:
        """Получить тип отношений"""
        return RelationshipType.from_value(self.value)
    
    def to_dict(self) -> Dict:
        return {
            "from": self.from_entity,
            "to": self.to_entity,
            "value": self.value,
            "type": self.get_type().value,
            "last_updated": self.last_updated.isoformat(),
            "history": self.history[-10:],  # последние 10 событий
            "metadata": self.metadata
        }

@dataclass
class RelationshipGraph:
    """Граф всех отношений"""
    nodes: List[str] = field(default_factory=list)  # все участники
    edges: Dict[str, Dict[str, Relationship]] = field(default_factory=dict)
    
    def get_relationship(self, from_entity: str, to_entity: str) -> Relationship:
        """Получить отношения между сущностями"""
        if from_entity not in self.edges:
            self.edges[from_entity] = {}
        if to_entity not in self.edges[from_entity]:
            self.edges[from_entity][to_entity] = Relationship(
                from_entity=from_entity,
                to_entity=to_entity
            )
            if from_entity not in self.nodes:
                self.nodes.append(from_entity)
            if to_entity not in self.nodes:
                self.nodes.append(to_entity)
        return self.edges[from_entity][to_entity]
    
    def update_relationship(self, from_entity: str, to_entity: str, 
                           delta: float, reason: str = "", source: str = "system"):
        """Обновить отношения"""
        rel = self.get_relationship(from_entity, to_entity)
        return rel.update(delta, reason, source)
    
    def get_all_relationships(self, entity: str) -> Dict[str, float]:
        """Получить все отношения сущности к другим"""
        result = {}
        if entity in self.edges:
            for target, rel in self.edges[entity].items():
                result[target] = rel.value
        return result
    
    def get_network_stats(self) -> Dict:
        """Получить статистику по сети отношений"""
        if not self.nodes:
            return {}
        
        # Среднее значение
        values = []
        for from_entity in self.edges:
            for rel in self.edges[from_entity].values():
                values.append(rel.value)
        
        avg_value = sum(values) / len(values) if values else 0
        
        # Самый популярный
        popularity = {node: 0 for node in self.nodes}
        for from_entity in self.edges:
            for to_entity, rel in self.edges[from_entity].items():
                popularity[to_entity] += rel.value
        
        most_popular = max(popularity, key=popularity.get) if popularity else None
        
        # Самый противоречивый
        controversy = {node: 0 for node in self.nodes}
        for from_entity in self.edges:
            for to_entity, rel in self.edges[from_entity].items():
                controversy[to_entity] += abs(rel.value)
        
        most_controversial = max(controversy, key=controversy.get) if controversy else None
        
        return {
            "total_entities": len(self.nodes),
            "total_relationships": len(values),
            "average_value": avg_value,
            "most_popular": most_popular,
            "most_controversial": most_controversial,
            "positive_relationships": sum(1 for v in values if v > 0.2),
            "negative_relationships": sum(1 for v in values if v < -0.2),
            "neutral_relationships": sum(1 for v in values if -0.2 <= v <= 0.2)
        }
    
    def to_dict(self) -> Dict:
        """Экспорт в словарь для API"""
        return {
            "nodes": self.nodes,
            "edges": {
                from_entity: {
                    to_entity: rel.to_dict()
                    for to_entity, rel in rels.items()
                }
                for from_entity, rels in self.edges.items()
            },
            "stats": self.get_network_stats()
        }

@dataclass
class AnalysisResult:
    """Результат анализа сообщения"""
    message_id: str
    sender: str
    content: str
    timestamp: datetime
    
    # Влияние на каждого
    impacts: Dict[str, float]
    
    # Общая тональность
    sentiment: float
    
    # Эмоции
    emotions: Dict[str, float]
    
    # Объяснение
    reason: str
    
    # Метаданные
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "content": self.content[:100] + "...",
            "timestamp": self.timestamp.isoformat(),
            "impacts": self.impacts,
            "sentiment": self.sentiment,
            "emotions": self.emotions,
            "reason": self.reason,
            "metadata": self.metadata
        }
