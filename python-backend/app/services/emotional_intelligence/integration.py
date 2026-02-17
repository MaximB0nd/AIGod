"""
Интеграция эмоционального интеллекта с модулем оркестрации
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from .manager import EmotionalIntelligenceManager
from .analyzer import EmotionAnalyzer
from .models import EmotionAnalysisResult, EmotionType

class EmotionalOrchestrationIntegration:
    """
    Интеграция эмоционального интеллекта с OrchestrationClient
    """
    
    def __init__(self, 
                 emotional_manager: EmotionalIntelligenceManager,
                 auto_analyze: bool = True):
        
        self.manager = emotional_manager
        self.auto_analyze = auto_analyze
        
        # Статистика интеграции
        self.stats = {
            "messages_processed": 0,
            "emotions_updated": 0,
            "emotional_contagions": 0
        }
    
    def register_agents(self, agent_names: List[str]):
        """Зарегистрировать агентов"""
        self.manager.register_entities(agent_names)
    
    async def on_agent_message(self,
                               message: str,
                               sender: str,
                               conversation_id: str,
                               participants: List[str],
                               message_id: Optional[str] = None) -> Optional[Dict]:
        """
        Обработчик сообщения от агента
        """
        self.stats["messages_processed"] += 1
        
        if not self.auto_analyze or not self.manager.analyzer:
            return None
        
        # Анализируем эмоции
        result = await self.manager.process_message(
            message=message,
            sender=sender,
            conversation_id=conversation_id,
            participants=participants,
            message_id=message_id
        )
        
        if result:
            self.stats["emotions_updated"] += len(result.detected_emotions)
            
            # Возвращаем информацию
            return {
                "message_id": result.message_id,
                "sender": sender,
                "detected_emotions": {e.value: v for e, v in result.detected_emotions.items()},
                "primary_emotion": result.primary_emotion.value,
                "intensity": result.intensity,
                "sentiment": result.sentiment,
                "emotional_impact": {
                    target: {e.value: v for e, v in emotions.items()}
                    for target, emotions in result.emotional_impact.items()
                }
            }
        
        return None
    
    async def on_user_message(self,
                              message: str,
                              conversation_id: str,
                              participants: List[str],
                              user_name: str = "user") -> Optional[Dict]:
        """
        Обработчик сообщения от пользователя
        """
        return await self.on_agent_message(
            message=message,
            sender=user_name,
            conversation_id=conversation_id,
            participants=participants
        )
    
    def get_agent_emotional_state(self, agent_name: str) -> Dict:
        """Получить эмоциональное состояние агента"""
        return self.manager.get_emotional_summary(agent_name)
    
    def get_conversation_atmosphere(self, conversation_id: str) -> Dict:
        """Получить атмосферу разговора"""
        return self.manager.get_conversation_atmosphere(conversation_id)
    
    def get_all_emotional_states(self) -> Dict:
        """Получить все состояния"""
        return self.manager.get_all_states()
    
    def enhance_prompt_with_emotions(self,
                                     agent_name: str,
                                     original_prompt: str) -> str:
        """
        Обогатить промпт информацией об эмоциональном состоянии
        """
        state = self.manager.get_state(agent_name)
        profile = self.manager.get_profile(agent_name)
        
        if not state:
            return original_prompt
        
        # Формируем описание эмоционального состояния
        dominant = state.get_dominant_emotion()
        mood = state.get_mood()
        
        emotion_text = [
            f"\n[Твоё эмоциональное состояние:]",
            f"Настроение: {mood}",
        ]
        
        if dominant:
            emotion_text.append(f"Доминирующая эмоция: {dominant.value}")
        
        emotion_text.append(f"Эмоциональный интеллект: {state.get_emotional_intelligence_score():.2f}")
        
        if profile:
            emotion_text.append(f"Твой стиль общения: {profile.communication_style}")
        
        emotion_text.append("\nУчитывай своё состояние в ответе.\n")
        
        return "\n".join(emotion_text) + original_prompt
    
    def get_emotional_intelligence_report(self, agent_name: str) -> str:
        """
        Получить отчёт по эмоциональному интеллекту
        """
        state = self.manager.get_state(agent_name)
        profile = self.manager.get_profile(agent_name)
        
        if not state:
            return f"Нет данных для {agent_name}"
        
        lines = [
            f"\n📊 **Эмоциональный отчёт для {agent_name}**",
            f"=" * 40,
            f"",
            f"Текущее состояние:"
        ]
        
        # Эмоции
        for emotion, value in state.emotions.items():
            if value > 0.1:
                bar = "█" * int(value * 20)
                lines.append(f"  {emotion.value:12}: {bar} {value:.2f}")
        
        lines.extend([
            f"",
            f"Доминирующая эмоция: {state.get_dominant_emotion().value if state.get_dominant_emotion() else 'нет'}",
            f"Настроение: {state.get_mood()}",
            f"Интенсивность: {state.intensity:.2f}",
            f"Эмоциональный интеллект: {state.get_emotional_intelligence_score():.2f}",
            f"",
            f"Профиль личности:"
        ])
        
        if profile:
            lines.extend([
                f"  Открытость: {profile.openness:.2f}",
                f"  Добросовестность: {profile.conscientiousness:.2f}",
                f"  Экстраверсия: {profile.extraversion:.2f}",
                f"  Доброжелательность: {profile.agreeableness:.2f}",
                f"  Нейротизм: {profile.neuroticism:.2f}",
                f"  Стиль общения: {profile.communication_style}"
            ])
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "analyzer_stats": self.manager.analyzer.get_stats() if self.manager.analyzer else None,
            "emotional_stats": self.manager.get_stats()
        }
