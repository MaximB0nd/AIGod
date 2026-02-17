"""
Поток мыслей агента - внутренний монолог и обработка информации
"""
import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import heapq
import uuid

from .models import Thought, ThoughtType, CognitiveState

class MemoryStream:
    """
    Поток мыслей агента - аналог человеческого потока сознания
    """
    
    def __init__(self, agent_name: str, decay_rate: float = 0.1):
        self.agent_name = agent_name
        self.decay_rate = decay_rate  # скорость затухания важности
        
        # Поток мыслей (сортированная очередь по важности)
        self.thought_stream: List[tuple] = []  # (importance, timestamp, thought)
        
        # Краткосрочная память (последние мысли)
        self.short_term: List[Thought] = []
        
        # Долгосрочная память (важные мысли)
        self.long_term: Dict[str, Thought] = {}
        
        # Внутренний диалог
        self.inner_dialogue: List[str] = []
        
        # Статистика
        self.stats = {
            "total_thoughts": 0,
            "important_thoughts": 0,
            "average_importance": 0
        }
    
    def add_thought(self, content: str, 
                   thought_type: ThoughtType,
                   importance: float = 0.5,
                   context: Optional[Dict] = None) -> Thought:
        """
        Добавить мысль в поток
        """
        thought = Thought(
            id=f"thought_{uuid.uuid4().hex[:8]}_{datetime.now().timestamp()}",
            agent_name=self.agent_name,
            type=thought_type,
            content=content,
            timestamp=datetime.now(),
            importance=importance,
            context=context or {}
        )
        
        # Добавляем в очередь с приоритетом (важность)
        heapq.heappush(self.thought_stream, 
                      (-importance, thought.timestamp.timestamp(), thought))
        
        # Добавляем в краткосрочную
        self.short_term.append(thought)
        if len(self.short_term) > 50:
            self.short_term = self.short_term[-50:]
        
        # Если важная, сохраняем в долгосрочную
        if importance > 0.7:
            self.long_term[thought.id] = thought
            self.stats["important_thoughts"] += 1
        
        # Обновляем статистику
        self.stats["total_thoughts"] += 1
        self._update_stats()
        
        return thought
    
    def get_next_thought(self) -> Optional[Thought]:
        """
        Получить следующую мысль для обработки (с учётом затухания)
        """
        if not self.thought_stream:
            return None
        
        # Применяем затухание к важности
        now = datetime.now()
        adjusted_stream = []
        
        while self.thought_stream:
            neg_importance, ts, thought = heapq.heappop(self.thought_stream)
            age = (now - thought.timestamp).seconds / 3600  # часы
            decay = 1.0 / (1.0 + self.decay_rate * age)
            adjusted_importance = -neg_importance * decay
            
            adjusted_stream.append((adjusted_importance, ts, thought))
        
        # Сортируем заново
        adjusted_stream.sort(key=lambda x: x[0], reverse=True)
        
        # Берём самую важную
        if adjusted_stream:
            imp, ts, thought = adjusted_stream[0]
            # Возвращаем остальные в поток
            for a, t, th in adjusted_stream[1:]:
                heapq.heappush(self.thought_stream, (-a, t, th))
            
            return thought
        
        return None
    
    def get_recent_thoughts(self, limit: int = 10, 
                           thought_type: Optional[ThoughtType] = None) -> List[Thought]:
        """
        Получить последние мысли
        """
        recent = sorted(self.short_term, key=lambda x: x.timestamp, reverse=True)
        
        if thought_type:
            recent = [t for t in recent if t.type == thought_type]
        
        return recent[:limit]
    
    def get_important_thoughts(self, threshold: float = 0.7) -> List[Thought]:
        """
        Получить важные мысли
        """
        return [t for t in self.long_term.values() if t.importance > threshold]
    
    def search_thoughts(self, query: str) -> List[Thought]:
        """
        Простой поиск по мыслям
        """
        query_lower = query.lower()
        results = []
        
        for thought in list(self.long_term.values()) + self.short_term:
            if query_lower in thought.content.lower():
                results.append(thought)
        
        return results[:10]
    
    def add_to_inner_dialogue(self, line: str):
        """Добавить строку во внутренний диалог"""
        self.inner_dialogue.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
        if len(self.inner_dialogue) > 30:
            self.inner_dialogue = self.inner_dialogue[-30:]
    
    def get_inner_dialogue(self) -> str:
        """Получить внутренний диалог как текст"""
        return "\n".join(self.inner_dialogue)
    
    def _update_stats(self):
        """Обновить статистику"""
        if self.short_term:
            avg_imp = sum(t.importance for t in self.short_term) / len(self.short_term)
            self.stats["average_importance"] = avg_imp
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "short_term_size": len(self.short_term),
            "long_term_size": len(self.long_term),
            "stream_size": len(self.thought_stream)
        }

class ThoughtProcessor:
    """
    Обработчик мыслей - связывает мысли с действиями
    """
    
    def __init__(self, memory_stream: MemoryStream):
        self.memory_stream = memory_stream
        self.processors = {
            ThoughtType.OBSERVATION: self._process_observation,
            ThoughtType.REFLECTION: self._process_reflection,
            ThoughtType.PLAN: self._process_plan,
            ThoughtType.DECISION: self._process_decision,
            ThoughtType.QUESTION: self._process_question,
        }
    
    async def process_thought(self, thought: Thought) -> Optional[Dict]:
        """
        Обработать мысль
        """
        processor = self.processors.get(thought.type)
        if processor:
            return await processor(thought)
        return None
    
    async def _process_observation(self, thought: Thought) -> Dict:
        """Обработать наблюдение"""
        self.memory_stream.add_to_inner_dialogue(
            f"👀 Наблюдаю: {thought.content}"
        )
        return {
            "action": "store_observation",
            "thought_id": thought.id
        }
    
    async def _process_reflection(self, thought: Thought) -> Dict:
        """Обработать рефлексию"""
        self.memory_stream.add_to_inner_dialogue(
            f"🤔 Размышляю: {thought.content}"
        )
        return {
            "action": "update_beliefs",
            "thought_id": thought.id
        }
    
    async def _process_plan(self, thought: Thought) -> Dict:
        """Обработать план"""
        self.memory_stream.add_to_inner_dialogue(
            f"📋 Планирую: {thought.content}"
        )
        return {
            "action": "create_plan",
            "thought_id": thought.id
        }
    
    async def _process_decision(self, thought: Thought) -> Dict:
        """Обработать решение"""
        self.memory_stream.add_to_inner_dialogue(
            f"⚖️ Принимаю решение: {thought.content}"
        )
        return {
            "action": "make_decision",
            "thought_id": thought.id
        }
    
    async def _process_question(self, thought: Thought) -> Dict:
        """Обработать вопрос"""
        self.memory_stream.add_to_inner_dialogue(
            f"❓ Возникает вопрос: {thought.content}"
        )
        return {
            "action": "seek_answer",
            "thought_id": thought.id
        }
