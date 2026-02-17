"""
Модуль для компрессии контекста
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import heapq

from .models import ContextWindow, Summary, MemoryItem, ImportanceLevel

class ContextCompressor:
    """
    Компрессор контекста - решает, что оставить, а что сжать
    """
    
    def __init__(self, 
                 summarizer: Optional['ContextSummarizer'] = None,
                 importance_threshold: ImportanceLevel = ImportanceLevel.MEDIUM):
        
        self.summarizer = summarizer
        self.importance_threshold = importance_threshold
    
    def compress_context(self, 
                        context_window: ContextWindow,
                        force: bool = False) -> ContextWindow:
        """
        Сжать контекстное окно
        """
        if not force and not context_window.should_summarize():
            return context_window
        
        # Оцениваем важность каждого сообщения
        scored_messages = self._score_messages(context_window.messages)
        
        # Сортируем по важности
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # Оставляем только важные сообщения
        important_messages = []
        important_scores = []
        tokens_used = 0
        
        for score, msg, tokens in scored_messages:
            if tokens_used + tokens <= context_window.max_tokens * 0.7:  # 70% для важных
                important_messages.append(msg)
                important_scores.append(score)
                tokens_used += tokens
            else:
                break
        
        # Остальное отправляем на суммаризацию
        if len(important_messages) < len(context_window.messages):
            # Создаём чанк для суммаризации
            chunk = self._create_summary_chunk(
                context_window.messages,
                context_window
            )
            
            if self.summarizer:
                # Асинхронно суммаризируем
                import asyncio
                asyncio.create_task(self._summarize_and_update(chunk, context_window))
        
        # Обновляем окно
        context_window.messages = important_messages
        
        return context_window
    
    def _score_messages(self, messages: List[Dict]) -> List[tuple]:
        """
        Оценить важность сообщений
        """
        scored = []
        
        for msg in messages:
            score = 0
            tokens = len(msg['content'].split()) * 1.3  # грубая оценка
            
            # Недавние сообщения важнее
            time_factor = 1.0
            if 'timestamp' in msg:
                age = (datetime.now() - msg['timestamp']).seconds
                time_factor = max(0.5, 1.0 - (age / 3600))  # за час важность падает до 0.5
            
            # Сообщения с вопросами важнее
            if '?' in msg['content']:
                score += 0.3
            
            # Сообщения с ключевыми словами
            important_keywords = ['важно', 'решение', 'согласны', 'нужно', 'обязательно']
            for kw in important_keywords:
                if kw in msg['content'].lower():
                    score += 0.2
            
            # Длинные сообщения обычно важнее
            length_factor = min(1.0, len(msg['content']) / 500)
            score += length_factor * 0.2
            
            # Итоговый счёт
            final_score = score * time_factor
            
            scored.append((final_score, msg, tokens))
        
        return scored
    
    def _create_summary_chunk(self, 
                             messages: List[Dict],
                             context_window: ContextWindow) -> 'ConversationChunk':
        """
        Создать чанк для суммаризации
        """
        from .models import ConversationChunk
        
        # Определяем участников
        participants = list(set(msg['sender'] for msg in messages))
        
        # Находим время
        timestamps = [msg.get('timestamp', datetime.now()) for msg in messages]
        start_time = min(timestamps)
        end_time = max(timestamps)
        
        # Считаем токены
        token_count = sum(len(msg['content'].split()) * 1.3 for msg in messages)
        
        return ConversationChunk(
            chunk_id=f"chunk_{datetime.now().timestamp()}",
            conversation_id=context_window.messages[0].get('conversation_id', 'unknown'),
            messages=messages,
            start_time=start_time,
            end_time=end_time,
            participants=participants,
            token_count=int(token_count)
        )
    
    async def _summarize_and_update(self, 
                                   chunk: 'ConversationChunk',
                                   context_window: ContextWindow):
        """
        Суммаризировать и обновить контекст
        """
        if not self.summarizer:
            return
        
        summary = await self.summarizer.summarize_chunk(chunk)
        
        if summary:
            context_window.summaries.append(summary)
    
    def get_optimal_context(self,
                           query: str,
                           recent_messages: List[Dict],
                           vector_memories: List[MemoryItem],
                           max_tokens: int) -> str:
        """
        Получить оптимальный контекст для промпта
        """
        parts = []
        tokens_used = 0
        
        # 1. Самые релевантные векторные воспоминания
        for memory in vector_memories:
            memory_tokens = len(memory.content.split()) * 1.3
            if tokens_used + memory_tokens <= max_tokens * 0.3:  # 30% на память
                parts.append(f"[Воспоминание] {memory.content}")
                tokens_used += memory_tokens
            else:
                break
        
        # 2. Последние важные сообщения
        scored_recent = self._score_messages(recent_messages)
        scored_recent.sort(key=lambda x: x[0], reverse=True)
        
        for score, msg, tokens in scored_recent[:10]:  # максимум 10 сообщений
            if tokens_used + tokens <= max_tokens * 0.5:  # 50% на недавние
                parts.append(f"{msg['sender']}: {msg['content']}")
                tokens_used += tokens
        
        # 3. Суммаризации если есть место
        if hasattr(context_window, 'summaries') and tokens_used < max_tokens:
            for summary in context_window.summaries[-2:]:  # последние 2
                summary_tokens = summary.token_count
                if tokens_used + summary_tokens <= max_tokens:
                    parts.append(f"[Сводка] {summary.content}")
                    tokens_used += summary_tokens
        
        return "\n".join(parts)
