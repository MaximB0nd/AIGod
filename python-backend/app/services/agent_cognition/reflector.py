"""
Система рефлексии агента - анализ прошлых действий
"""
import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid

from .models import Reflection, ReflectionType, Thought, Plan, Decision

class Reflector:
    """
    Рефлексия агента - анализ прошлого опыта
    """
    
    def __init__(self, agent_name: str, chat_service=None):
        self.agent_name = agent_name
        self.chat_service = chat_service
        
        # История рефлексий
        self.reflections: List[Reflection] = []
        
        # Интервал рефлексии (в секундах)
        self.reflection_interval = 300  # 5 минут
        
        # Последняя рефлексия
        self.last_reflection = datetime.now()
        
        # Статистика
        self.stats = {
            "total_reflections": 0,
            "self_reflections": 0,
            "other_reflections": 0,
            "learning_reflections": 0
        }
    
    async def reflect_on_action(self, 
                                action: Dict,
                                outcome: Dict,
                                context: Dict) -> Optional[Reflection]:
        """
        Рефлексия над действием
        """
        reflection_type = self._determine_reflection_type(action, outcome)
        
        content = await self._generate_reflection(
            action=action,
            outcome=outcome,
            reflection_type=reflection_type,
            context=context
        )
        
        if not content:
            return None
        
        # Извлекаем инсайты
        insights = await self._extract_insights(content, action, outcome)
        
        reflection = Reflection(
            reflection_id=f"refl_{uuid.uuid4().hex[:8]}_{datetime.now().timestamp()}",
            agent_name=self.agent_name,
            type=reflection_type,
            content=content,
            timestamp=datetime.now(),
            based_on=[action.get("id", "unknown")],
            insights=insights.get("insights", []),
            learnings=insights.get("learnings", []),
            confidence=insights.get("confidence", 0.5)
        )
        
        self.reflections.append(reflection)
        self.stats["total_reflections"] += 1
        self.stats[f"{reflection_type.value}_reflections"] = \
            self.stats.get(f"{reflection_type.value}_reflections", 0) + 1
        
        return reflection
    
    async def reflect_on_period(self, 
                                actions: List[Dict],
                                plans: List[Plan],
                                decisions: List[Decision],
                                period_hours: int = 1) -> Optional[Reflection]:
        """
        Рефлексия за период времени
        """
        if not actions and not plans and not decisions:
            return None
        
        # Создаём сводку за период
        summary = await self._create_period_summary(actions, plans, decisions)
        
        if not summary:
            return None
        
        reflection = Reflection(
            reflection_id=f"refl_period_{uuid.uuid4().hex[:8]}",
            agent_name=self.agent_name,
            type=ReflectionType.LEARNING,
            content=summary,
            timestamp=datetime.now(),
            based_on=[a.get("id") for a in actions[:5]],  # топ-5 действий
            insights=[],
            learnings=[],
            confidence=0.7
        )
        
        self.reflections.append(reflection)
        self.stats["total_reflections"] += 1
        self.stats["learning_reflections"] += 1
        
        return reflection
    
    async def reflect_on_mistake(self, 
                                 action: Dict,
                                 error: str,
                                 context: Dict) -> Optional[Reflection]:
        """
        Рефлексия над ошибкой
        """
        content = await self._analyze_mistake(action, error, context)
        
        if not content:
            return None
        
        reflection = Reflection(
            reflection_id=f"refl_mistake_{uuid.uuid4().hex[:8]}",
            agent_name=self.agent_name,
            type=ReflectionType.MISTAKE,
            content=content,
            timestamp=datetime.now(),
            based_on=[action.get("id", "unknown")],
            insights=[],
            learnings=[f"Избегать: {error}"],
            confidence=0.8
        )
        
        self.reflections.append(reflection)
        self.stats["total_reflections"] += 1
        self.stats["mistake_reflections"] = self.stats.get("mistake_reflections", 0) + 1
        
        return reflection
    
    def _determine_reflection_type(self, action: Dict, outcome: Dict) -> ReflectionType:
        """Определить тип рефлексии"""
        if "self" in action.get("target", "").lower():
            return ReflectionType.SELF
        elif "other" in action.get("target", "").lower():
            return ReflectionType.OTHER
        elif "relationship" in action.get("type", "").lower():
            return ReflectionType.RELATIONSHIP
        elif outcome.get("success", False):
            return ReflectionType.LEARNING
        else:
            return ReflectionType.MISTAKE
    
    async def _generate_reflection(self, 
                                   action: Dict,
                                   outcome: Dict,
                                   reflection_type: ReflectionType,
                                   context: Dict) -> Optional[str]:
        """Сгенерировать рефлексию через AI"""
        if not self.chat_service:
            return f"Я {reflection_type.value} над действием: {action.get('description', '')}"
        
        prompt = f"""
        Ты проводишь рефлексию над своим действием.
        
        Тип рефлексии: {reflection_type.value}
        
        Действие: {action.get('description', '')}
        Результат: {outcome.get('description', '')}
        Успех: {outcome.get('success', False)}
        
        Контекст: {context.get('situation', '')}
        
        Напиши краткую рефлексию (2-3 предложения) о том, что ты узнал из этого опыта.
        """
        
        try:
            response = await self.chat_service(
                agent_name="reflector",
                session_id=f"reflect_{self.agent_name}",
                prompt=prompt
            )
            return response.strip()
        except Exception as e:
            print(f"Error generating reflection: {e}")
            return None
    
    async def _extract_insights(self, 
                                reflection: str,
                                action: Dict,
                                outcome: Dict) -> Dict:
        """Извлечь инсайты из рефлексии"""
        # В базовой реализации просто возвращаем структуру
        return {
            "insights": [f"Из действия: {action.get('description', '')}"],
            "learnings": [f"Результат: {outcome.get('description', '')}"],
            "confidence": 0.6
        }
    
    async def _create_period_summary(self,
                                     actions: List[Dict],
                                     plans: List[Plan],
                                     decisions: List[Decision]) -> Optional[str]:
        """Создать сводку за период"""
        if not self.chat_service:
            return f"Проанализировано {len(actions)} действий и {len(plans)} планов"
        
        actions_summary = "\n".join([f"- {a.get('description', '')}" for a in actions[:10]])
        plans_summary = "\n".join([f"- {p.goal}" for p in plans[:5]])
        
        prompt = f"""
        Проанализируй мои действия за последний час.
        
        Действия:
        {actions_summary}
        
        Планы:
        {plans_summary}
        
        Создай краткую рефлексию (3-4 предложения) о том:
        - Что было сделано хорошо
        - Что можно улучшить
        - Какие выводы я могу сделать
        """
        
        try:
            response = await self.chat_service(
                agent_name="reflector",
                session_id=f"period_reflect_{self.agent_name}",
                prompt=prompt
            )
            return response.strip()
        except Exception as e:
            print(f"Error creating period summary: {e}")
            return None
    
    async def _analyze_mistake(self, action: Dict, error: str, context: Dict) -> Optional[str]:
        """Проанализировать ошибку"""
        if not self.chat_service:
            return f"Ошибка в действии: {error}"
        
        prompt = f"""
        Проанализируй мою ошибку.
        
        Действие: {action.get('description', '')}
        Ошибка: {error}
        Контекст: {context.get('situation', '')}
        
        Напиши анализ (2-3 предложения):
        - Почему произошла ошибка
        - Как её избежать в будущем
        """
        
        try:
            response = await self.chat_service(
                agent_name="reflector",
                session_id=f"mistake_analyze_{self.agent_name}",
                prompt=prompt
            )
            return response.strip()
        except Exception as e:
            print(f"Error analyzing mistake: {e}")
            return None
    
    def get_recent_reflections(self, limit: int = 5) -> List[Reflection]:
        """Получить последние рефлексии"""
        return sorted(self.reflections, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_reflections_by_type(self, reflection_type: ReflectionType) -> List[Reflection]:
        """Получить рефлексии по типу"""
        return [r for r in self.reflections if r.type == reflection_type]
    
    def should_reflect(self) -> bool:
        """Проверить, пора ли рефлексировать"""
        now = datetime.now()
        return (now - self.last_reflection).seconds > self.reflection_interval
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "reflections_count": len(self.reflections),
            "time_since_last": (datetime.now() - self.last_reflection).seconds,
            "average_confidence": sum(r.confidence for r in self.reflections) / len(self.reflections) if self.reflections else 0
        }
