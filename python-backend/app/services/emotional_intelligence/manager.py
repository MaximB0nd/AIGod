"""
Менеджер эмоционального интеллекта
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import asyncio

from .models import (
    EmotionalState, EmotionalProfile, EmotionAnalysisResult, 
    EmotionType, EmotionalContext, EmotionType
)
from .analyzer import EmotionAnalyzer
from .events import EmotionalEvent, EventType

class EmotionalIntelligenceManager:
    """
    Главный класс для управления эмоциональным интеллектом агентов
    """
    
    def __init__(self, analyzer: Optional[EmotionAnalyzer] = None):
        self.analyzer = analyzer
        
        # Состояния всех сущностей
        self.states: Dict[str, EmotionalState] = {}
        
        # Профили всех сущностей
        self.profiles: Dict[str, EmotionalProfile] = {}
        
        # Контексты разговоров
        self.conversation_contexts: Dict[str, EmotionalContext] = {}
        
        # История всех изменений
        self.history: List[Dict] = []
        
        # Подписчики на события
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        
        # Задачи для фоновых процессов
        self._decay_task = None
        self._running = False
        
        # Если есть анализатор, подписываемся
        if analyzer:
            analyzer.on_analysis(self._on_analysis_result)
    
    async def start(self):
        """Запустить менеджер"""
        self._running = True
        self._decay_task = asyncio.create_task(self._decay_loop())
    
    async def stop(self):
        """Остановить менеджер"""
        self._running = False
        if self._decay_task:
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass
    
    async def _decay_loop(self):
        """Фоновое затухание эмоций"""
        while self._running:
            await asyncio.sleep(60)  # каждую минуту
            for state in self.states.values():
                state.apply_decay(0.05)
    
    def register_entity(self, 
                        name: str, 
                        profile: Optional[EmotionalProfile] = None):
        """Зарегистрировать новую сущность"""
        if name not in self.states:
            self.states[name] = EmotionalState(entity=name)
            
            if profile:
                self.profiles[name] = profile
            else:
                # Профиль по умолчанию
                self.profiles[name] = EmotionalProfile(entity=name)
            
            self._trigger_event(EventType.ENTITY_ADDED, {"entity": name})
    
    def register_entities(self, names: List[str]):
        """Зарегистрировать несколько сущностей"""
        for name in names:
            self.register_entity(name)
    
    def get_state(self, entity: str) -> Optional[EmotionalState]:
        """Получить эмоциональное состояние"""
        return self.states.get(entity)
    
    def get_profile(self, entity: str) -> Optional[EmotionalProfile]:
        """Получить эмоциональный профиль"""
        return self.profiles.get(entity)
    
    def update_emotion(self, 
                      entity: str,
                      emotion: EmotionType,
                      delta: float,
                      reason: str = "",
                      source: str = "system"):
        """Обновить конкретную эмоцию"""
        if entity not in self.states:
            self.register_entity(entity)
        
        state = self.states[entity]
        state.update({emotion: delta}, reason, source)
        
        self._trigger_event(EventType.EMOTION_UPDATED, {
            "entity": entity,
            "emotion": emotion.value,
            "delta": delta,
            "new_value": state.emotions.get(emotion, 0),
            "reason": reason
        })
    
    def update_emotions(self,
                       entity: str,
                       updates: Dict[EmotionType, float],
                       reason: str = "",
                       source: str = "system"):
        """Обновить несколько эмоций"""
        if entity not in self.states:
            self.register_entity(entity)
        
        state = self.states[entity]
        state.update(updates, reason, source)
        
        self._trigger_event(EventType.EMOTION_UPDATED, {
            "entity": entity,
            "updates": {e.value: d for e, d in updates.items()},
            "reason": reason
        })
    
    def get_conversation_context(self, conversation_id: str, 
                                  participants: List[str]) -> EmotionalContext:
        """Получить или создать контекст разговора"""
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = EmotionalContext(
                conversation_id=conversation_id,
                participants=participants
            )
        return self.conversation_contexts[conversation_id]
    
    async def process_message(self,
                             message: str,
                             sender: str,
                             conversation_id: str,
                             participants: List[str],
                             message_id: Optional[str] = None) -> Optional[EmotionAnalysisResult]:
        """
        Обработать сообщение и обновить эмоциональные состояния
        """
        if not self.analyzer:
            return None
        
        # Анализируем эмоции в сообщении
        use_api = getattr(self.analyzer, "use_api", True)
        result = await self.analyzer.analyze_message(
            message=message,
            sender=sender,
            participants=participants,
            use_api=use_api,
            message_id=message_id,
        )
        
        if result:
            # Обновляем состояние отправителя
            self.update_emotions(
                entity=sender,
                updates=result.detected_emotions,
                reason=result.reason,
                source="message_analysis"
            )
            
            # Рассчитываем влияние на других участников
            await self._calculate_emotional_impact(result, participants)
            
            # Обновляем контекст разговора
            await self._update_conversation_context(result, conversation_id)
        
        return result
    
    async def _calculate_emotional_impact(self, 
                                          result: EmotionAnalysisResult,
                                          participants: List[str]):
        """Рассчитать влияние эмоций на других участников"""
        for target in participants:
            if target == result.sender:
                continue
            
            # Эмоциональное заражение
            if target in self.states:
                target_state = self.states[target]
                
                # Сильные эмоции заражают других
                for emotion, intensity in result.detected_emotions.items():
                    if intensity > 0.5:
                        # Коэффициент заражения зависит от близости и восприимчивости
                        infection_rate = 0.3 * (1 - target_state.resilience)
                        impact = intensity * infection_rate
                        
                        self.update_emotion(
                            entity=target,
                            emotion=emotion,
                            delta=impact,
                            reason=f"Эмоциональное заражение от {result.sender}",
                            source="emotional_contagion"
                        )
    
    async def _update_conversation_context(self, 
                                           result: EmotionAnalysisResult,
                                           conversation_id: str):
        """Обновить контекст разговора"""
        context = self.conversation_contexts.get(conversation_id)
        if not context:
            return
        
        # Обновляем эмоциональную температуру
        context.emotional_temperature = (
            context.emotional_temperature * 0.7 + result.intensity * 0.3
        )
        
        # Определяем атмосферу
        if result.sentiment > 0.3:
            context.atmosphere = "позитивная"
        elif result.sentiment < -0.3:
            context.atmosphere = "негативная"
        else:
            context.atmosphere = "нейтральная"
        
        # Сохраняем ключевой момент
        if result.intensity > 0.7:
            context.key_moments.append({
                "timestamp": result.timestamp.isoformat(),
                "sender": result.sender,
                "emotion": result.primary_emotion.value,
                "intensity": result.intensity,
                "message": result.content[:50] + "..."
            })
    
    def _on_analysis_result(self, result: EmotionAnalysisResult):
        """Обработчик результатов анализа"""
        # Автоматически обновляем состояние
        self.update_emotions(
            entity=result.sender,
            updates=result.detected_emotions,
            reason=result.reason,
            source="auto_analysis"
        )
        
        self._trigger_event(EventType.ANALYSIS_COMPLETED, result.to_dict())
    
    def get_emotional_summary(self, entity: str) -> Dict:
        """Получить сводку по эмоциональному состоянию"""
        state = self.states.get(entity)
        profile = self.profiles.get(entity)
        
        if not state:
            return {"entity": entity, "error": "Entity not found"}
        
        return {
            "entity": entity,
            "current_state": state.to_dict(),
            "profile": profile.to_dict() if profile else None,
            "emotional_intelligence": state.get_emotional_intelligence_score()
        }
    
    def get_conversation_atmosphere(self, conversation_id: str) -> Dict:
        """Получить атмосферу разговора"""
        context = self.conversation_contexts.get(conversation_id)
        if not context:
            return {}
        
        return context.to_dict()
    
    def get_all_states(self) -> Dict[str, Dict]:
        """Получить все состояния для API"""
        return {
            name: state.to_dict() 
            for name, state in self.states.items()
        }
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            "total_entities": len(self.states),
            "total_conversations": len(self.conversation_contexts),
            "average_eq": sum(
                s.get_emotional_intelligence_score() 
                for s in self.states.values()
            ) / len(self.states) if self.states else 0,
            "history_size": len(self.history),
            "analyzer_stats": self.analyzer.get_stats() if self.analyzer else None
        }
    
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
        data = {
            "states": {name: state.to_dict() for name, state in self.states.items()},
            "profiles": {name: profile.to_dict() for name, profile in self.profiles.items()},
            "conversations": {cid: ctx.to_dict() for cid, ctx in self.conversation_contexts.items()},
            "stats": self.get_stats()
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
