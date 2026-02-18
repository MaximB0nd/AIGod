"""
Менеджер отношений - основной класс для работы с отношениями
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio

from .models import RelationshipGraph, AnalysisResult
from .analyzer import RelationshipAnalyzer
from .events import RelationshipEvent, EventType

class RelationshipManager:
    """
    Главный класс для управления отношениями между агентами
    """
    
    def __init__(self, analyzer: Optional[RelationshipAnalyzer] = None):
        self.graph = RelationshipGraph()
        self.analyzer = analyzer
        
        # История всех изменений
        self.history: List[Dict] = []
        
        # Подписчики на события
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        
        # Если есть анализатор, подписываемся на его результаты (LLM RelationshipAnalyzer)
        if analyzer:
            analyzer.on_analysis(self._on_analysis_result)
    
    def register_participant(self, name: str):
        """Зарегистрировать нового участника"""
        if name not in self.graph.nodes:
            self.graph.nodes.append(name)
            self._trigger_event(EventType.PARTICIPANT_ADDED, {"participant": name})
    
    def register_participants(self, names: List[str]):
        """Зарегистрировать нескольких участников"""
        for name in names:
            self.register_participant(name)
    
    def update_relationship(self, from_entity: str, to_entity: str, 
                           delta: float, reason: str = "", source: str = "system"):
        """Обновить отношения между сущностями"""
        if from_entity not in self.graph.nodes:
            self.register_participant(from_entity)
        if to_entity not in self.graph.nodes:
            self.register_participant(to_entity)
        
        change = self.graph.update_relationship(
            from_entity, to_entity, delta, reason, source
        )
        
        # Сохраняем в историю
        event = {
            "timestamp": datetime.now().isoformat(),
            "from": from_entity,
            "to": to_entity,
            "delta": delta,
            "change": change,
            "new_value": self.get_relationship_value(from_entity, to_entity),
            "reason": reason,
            "source": source
        }
        self.history.append(event)
        
        # Триггерим событие
        self._trigger_event(EventType.RELATIONSHIP_UPDATED, event)
        
        return change
    
    def update_from_facts(self, facts: List[Any], participants: List[str]) -> int:
        """
        Обновить граф из структурированных фактов (триплетов).

        Факты: subject, predicate, object.
        Участники: список имён агентов для фильтрации.
        """
        count = 0
        for f in facts:
            subj = getattr(f, "subject", None) or (f.get("subject", "") if isinstance(f, dict) else "") or ""
            pred = getattr(f, "predicate", None) or (f.get("predicate", "") if isinstance(f, dict) else "") or ""
            obj_val = getattr(f, "obj", None) or getattr(f, "object", None) or (f.get("object", f.get("obj", "")) if isinstance(f, dict) else "") or ""
            if not subj or not pred:
                continue
            subj = str(subj).strip()
            obj_val = str(obj_val).strip()
            if subj in participants and obj_val in participants and subj != obj_val:
                delta = 0.1 if pred.lower() in ("agreed_with", "supported", "suggested") else -0.1 if pred.lower() in ("disagreed", "opposed") else 0.05
                self.update_relationship(subj, obj_val, delta, reason=pred, source="fact_extraction")
                count += 1
            elif subj in participants:
                self.register_participant(subj)
        return count

    def get_relationship_value(self, from_entity: str, to_entity: str) -> float:
        """Получить значение отношений"""
        rel = self.graph.get_relationship(from_entity, to_entity)
        return rel.value
    
    def get_relationship_type(self, from_entity: str, to_entity: str) -> str:
        """Получить тип отношений"""
        rel = self.graph.get_relationship(from_entity, to_entity)
        return rel.get_type().value
    
    def get_entity_relationships(self, entity: str) -> Dict[str, float]:
        """Получить все отношения сущности"""
        return self.graph.get_all_relationships(entity)
    
    def get_relationship_summary(self, entity: str) -> Dict:
        """Получить сводку по отношениям сущности"""
        rels = self.get_entity_relationships(entity)
        
        if not rels:
            return {
                "entity": entity,
                "total_relationships": 0,
                "average_value": 0,
                "relationships": {}
            }
        
        values = list(rels.values())
        
        return {
            "entity": entity,
            "total_relationships": len(rels),
            "average_value": sum(values) / len(values),
            "most_positive": max(rels, key=rels.get) if rels else None,
            "most_negative": min(rels, key=rels.get) if rels else None,
            "relationships": rels
        }
    
    def get_network_stats(self) -> Dict:
        """Получить статистику по всей сети"""
        return self.graph.get_network_stats()
    
    def get_full_state(self) -> Dict:
        """Получить полное состояние для API"""
        return {
            "graph": self.graph.to_dict(),
            "history": self.history[-100:],  # последние 100 событий
            "stats": self.get_network_stats()
        }
    
    async def process_message(self, 
                             message: str,
                             sender: str,
                             participants: List[str],
                             message_id: Optional[str] = None) -> Optional[AnalysisResult]:
        """
        Обработать сообщение и обновить отношения
        """
        if not self.analyzer:
            return None
        
        # Анализируем сообщение
        result = await self.analyzer.analyze_message(
            message=message,
            sender=sender,
            participants=participants,
            message_id=message_id
        )
        
        if result:
            # Применяем влияния
            for target, impact in result.impacts.items():
                if target in participants:
                    self.update_relationship(
                        from_entity=sender,
                        to_entity=target,
                        delta=impact * self.analyzer.influence_coefficient,
                        reason=result.reason,
                        source="analysis"
                    )
        
        return result
    
    def _on_analysis_result(self, result: AnalysisResult):
        """Обработчик результатов анализа"""
        # Применяем влияния автоматически
        for target, impact in result.impacts.items():
            self.update_relationship(
                from_entity=result.sender,
                to_entity=target,
                delta=impact * self.analyzer.influence_coefficient,
                reason=result.reason,
                source="auto_analysis"
            )
    
    # Система событий
    
    def on(self, event_type: EventType, handler: Callable):
        """Подписаться на событие"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: EventType, data: Any):
        """Вызвать событие"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    # Экспорт/импорт
    
    def export_to_json(self) -> str:
        """Экспортировать в JSON"""
        import json
        return json.dumps(self.get_full_state(), ensure_ascii=False, indent=2)
    
    def import_from_json(self, json_str: str):
        """Импортировать из JSON"""
        import json
        data = json.loads(json_str)
        # TODO: реализовать импорт
        pass
