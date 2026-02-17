"""
Модуль принятия решений агентом
"""
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import uuid
import math

from .models import Decision, Thought, Plan, Goal
from .memory_stream import MemoryStream

class DecisionMaker:
    """
    Принятие решений на основе мыслей, целей и контекста
    """
    
    def __init__(self, agent_name: str, chat_service=None):
        self.agent_name = agent_name
        self.chat_service = chat_service
        
        # История решений
        self.decisions: List[Decision] = []
        
        # Веса для принятия решений
        self.weights = {
            "goal_priority": 0.3,
            "past_success": 0.2,
            "emotional_state": 0.1,
            "risk": 0.2,
            "urgency": 0.2
        }
        
        # Статистика
        self.stats = {
            "decisions_made": 0,
            "successful_decisions": 0,
            "failed_decisions": 0
        }
    
    async def make_decision(self,
                           situation: str,
                           options: List[str],
                           context: Optional[Dict] = None,
                           goals: Optional[List[Goal]] = None,
                           memory_stream: Optional[MemoryStream] = None) -> Decision:
        """
        Принять решение на основе ситуации
        """
        # Оцениваем каждый вариант
        scored_options = await self._evaluate_options(
            situation, options, context, goals, memory_stream
        )
        
        # Выбираем лучший
        best_option = max(scored_options, key=lambda x: x[1])
        
        # Формируем обоснование
        reason = await self._generate_reason(
            situation, best_option[0], scored_options, context
        )
        
        decision = Decision(
            decision_id=f"dec_{uuid.uuid4().hex[:8]}_{datetime.now().timestamp()}",
            agent_name=self.agent_name,
            situation=situation,
            options=options,
            chosen=best_option[0],
            reason=reason,
            timestamp=datetime.now(),
            context=context or {}
        )
        
        self.decisions.append(decision)
        self.stats["decisions_made"] += 1
        
        return decision
    
    async def _evaluate_options(self,
                                situation: str,
                                options: List[str],
                                context: Optional[Dict],
                                goals: Optional[List[Goal]],
                                memory_stream: Optional[MemoryStream]) -> List[Tuple[str, float]]:
        """Оценить варианты решений"""
        
        if self.chat_service and len(options) > 1:
            # Используем AI для оценки
            return await self._ai_evaluate_options(situation, options, context)
        
        # Простая эвристическая оценка
        scored = []
        for option in options:
            score = 0.5  # базовый
            
            # Учёт целей
            if goals:
                for goal in goals:
                    if goal.description.lower() in option.lower():
                        score += 0.2 * (1 / goal.priority)
            
            # Учёт прошлых решений
            similar_decisions = [d for d in self.decisions 
                               if d.chosen.lower() in option.lower()]
            if similar_decisions:
                success_rate = sum(1 for d in similar_decisions if d.outcome == "success") / len(similar_decisions)
                score += 0.1 * success_rate
            
            scored.append((option, min(1.0, score)))
        
        return scored
    
    async def _ai_evaluate_options(self,
                                   situation: str,
                                   options: List[str],
                                   context: Optional[Dict]) -> List[Tuple[str, float]]:
        """Использовать AI для оценки вариантов"""
        
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        prompt = f"""
        Оцени варианты решения в ситуации.
        
        Ситуация: {situation}
        
        Варианты:
        {options_text}
        
        Контекст: {context if context else 'нет'}
        
        Оцени каждый вариант от 0 до 1, где 1 - наилучший.
        Ответь в формате JSON: {{"option_1": 0.8, "option_2": 0.3}}
        """
        
        try:
            response = await self.chat_service(
                agent_name="decision_maker",
                session_id=f"decide_{self.agent_name}",
                prompt=prompt
            )
            
            # Парсим JSON
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                scores = json.loads(json_match.group())
                return [(opt, scores.get(f"option_{i+1}", 0.5)) 
                       for i, opt in enumerate(options)]
            
        except Exception as e:
            print(f"Error in AI evaluation: {e}")
        
        # Fallback
        return [(opt, 0.5) for opt in options]
    
    async def _generate_reason(self,
                               situation: str,
                               chosen: str,
                               scored_options: List[Tuple[str, float]],
                               context: Optional[Dict]) -> str:
        """Сгенерировать обоснование решения"""
        
        if self.chat_service:
            options_summary = "\n".join([f"{opt}: {score:.2f}" for opt, score in scored_options])
            
            prompt = f"""
            Объясни, почему было принято это решение.
            
            Ситуация: {situation}
            Выбранный вариант: {chosen}
            Оценки вариантов:
            {options_summary}
            
            Напиши краткое обоснование (2-3 предложения).
            """
            
            try:
                response = await self.chat_service(
                    agent_name="decision_maker",
                    session_id=f"reason_{self.agent_name}",
                    prompt=prompt
                )
                return response.strip()
            except Exception:
                pass
        
        return f"Выбран вариант с наивысшей оценкой: {scored_options[0][1]:.2f}"
    
    def record_outcome(self, decision_id: str, outcome: str, success: bool):
        """
        Записать результат решения
        """
        for decision in self.decisions:
            if decision.decision_id == decision_id:
                decision.outcome = outcome
                if success:
                    self.stats["successful_decisions"] += 1
                else:
                    self.stats["failed_decisions"] += 1
                break
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """
        Получить историю решений
        """
        recent = sorted(self.decisions, key=lambda d: d.timestamp, reverse=True)[:limit]
        return [d.to_dict() for d in recent]
    
    def evaluate_decision_quality(self) -> Dict:
        """
        Оценить качество принимаемых решений
        """
        total = self.stats["decisions_made"]
        if total == 0:
            return {"error": "no decisions yet"}
        
        success_rate = self.stats["successful_decisions"] / total
        
        return {
            "total_decisions": total,
            "success_rate": success_rate,
            "successful": self.stats["successful_decisions"],
            "failed": self.stats["failed_decisions"],
            "average_confidence": 0.7  # можно вычислить реально
        }
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "total_decisions": len(self.decisions),
            "recent_decisions": len(self.get_decision_history(5))
        }
