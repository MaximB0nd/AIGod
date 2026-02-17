"""
Менеджер памяти - координация между краткосрочной и долгосрочной памятью
"""
import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid

from .models import (
    MemoryItem, MemoryType, ImportanceLevel, 
    MemoryStats, ContextWindow, Summary
)
from .vector_store import VectorMemoryStore
from .summarizer import ContextSummarizer
from .compression import ContextCompressor

class MemoryManager:
    """
    Менеджер памяти - управляет всей системой памяти
    """
    
    def __init__(self,
                 vector_store: Optional[VectorMemoryStore] = None,
                 summarizer: Optional[ContextSummarizer] = None,
                 conversation_id: str = "default"):
        
        self.vector_store = vector_store
        self.summarizer = summarizer
        self.conversation_id = conversation_id
        
        # Краткосрочная память (текущий контекст)
        self.short_term: List[MemoryItem] = []
        
        # Контекстное окно
        self.context_window = ContextWindow(max_tokens=4000)  # 4K токенов
        
        # Компрессор
        self.compressor = ContextCompressor(summarizer)
        
        # Статистика
        self.stats = {
            "short_term_items": 0,
            "long_term_items": 0,
            "summaries_created": 0,
            "context_compressions": 0
        }
        
        # Колбэки
        self.callbacks: List[Callable] = []
        
        # Задачи
        self._maintenance_task = None
        self._running = False
    
    def on_memory_update(self, callback: Callable[[MemoryItem], None]):
        """Подписаться на обновления памяти"""
        self.callbacks.append(callback)
    
    async def start(self):
        """Запустить менеджер"""
        self._running = True
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
    
    async def stop(self):
        """Остановить менеджер"""
        self._running = False
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
    
    async def add_message(self,
                         content: str,
                         sender: str,
                         importance: ImportanceLevel = ImportanceLevel.MEDIUM,
                         memory_type: MemoryType = MemoryType.SHORT_TERM,
                         metadata: Optional[Dict] = None) -> MemoryItem:
        """
        Добавить сообщение в память
        """
        # Создаём элемент памяти
        memory = MemoryItem(
            id=f"mem_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            content=content,
            type=memory_type,
            importance=importance,
            timestamp=datetime.now(),
            metadata=metadata or {},
            tags=self._extract_tags(content),
            participants=[sender],
            ttl=3600 if memory_type == MemoryType.SHORT_TERM else None  # 1 час для краткосрочной
        )
        
        # Добавляем в краткосрочную память
        self.short_term.append(memory)
        self.stats["short_term_items"] = len(self.short_term)
        
        # Добавляем в контекстное окно
        tokens = len(content.split()) * 1.3
        should_compress = self.context_window.add_message({
            "id": memory.id,
            "sender": sender,
            "content": content,
            "timestamp": memory.timestamp,
            "conversation_id": self.conversation_id
        }, int(tokens))
        
        # Если нужно сжать контекст
        if should_compress:
            await self.compress_context()
        
        # Если важное, сохраняем в долгосрочную
        if importance in [ImportanceLevel.HIGH, ImportanceLevel.CRITICAL]:
            await self.transfer_to_long_term(memory)
        
        # Вызываем колбэки
        for callback in self.callbacks:
            try:
                callback(memory)
            except Exception as e:
                print(f"Error in callback: {e}")
        
        return memory
    
    async def transfer_to_long_term(self, memory: MemoryItem):
        """
        Перенести в долгосрочную память
        """
        if not self.vector_store:
            return
        
        # Меняем тип
        memory.type = MemoryType.LONG_TERM
        memory.ttl = None  # бессрочно
        
        # Сохраняем в векторное хранилище
        self.vector_store.add_memory(memory)
        self.stats["long_term_items"] = self.vector_store.collection.count()
    
    async def compress_context(self):
        """
        Сжать контекст
        """
        # Сжимаем контекстное окно
        self.compressor.compress_context(self.context_window)
        self.stats["context_compressions"] += 1
        
        # Удаляем старые элементы из краткосрочной памяти
        self.short_term = [m for m in self.short_term if not m.is_expired()]
        self.stats["short_term_items"] = len(self.short_term)
    
    async def search_memory(self, 
                           query: str,
                           include_short_term: bool = True,
                           include_long_term: bool = True,
                           n_results: int = 5) -> List[MemoryItem]:
        """
        Поиск в памяти
        """
        results = []
        
        # Поиск в краткосрочной
        if include_short_term:
            # Простой поиск по ключевым словам
            query_words = set(query.lower().split())
            for mem in self.short_term:
                mem_words = set(mem.content.lower().split())
                overlap = len(query_words & mem_words)
                if overlap > 0:
                    results.append((overlap, mem))
            
            results.sort(key=lambda x: x[0], reverse=True)
        
        # Поиск в долгосрочной
        if include_long_term and self.vector_store:
            vector_results = self.vector_store.search_memory(
                query=query,
                n_results=n_results
            )
            
            # Конвертируем в MemoryItem
            for vr in vector_results:
                mem = MemoryItem(
                    id=vr["id"],
                    content=vr["content"],
                    type=MemoryType.LONG_TERM,
                    importance=ImportanceLevel(vr["metadata"]["importance"]),
                    timestamp=datetime.fromisoformat(vr["metadata"]["timestamp"]),
                    tags=vr["metadata"].get("tags", [])
                )
                results.append((vr.get("distance", 0), mem))
        
        # Убираем дубликаты и сортируем
        seen = set()
        unique_results = []
        for score, mem in results:
            if mem.id not in seen:
                seen.add(mem.id)
                unique_results.append(mem)
        
        return unique_results[:n_results]
    
    def get_relevant_context(self, query: str, max_tokens: int = 1000) -> str:
        """
        Получить релевантный контекст для промпта
        """
        # Ищем в памяти
        memories = asyncio.run(self.search_memory(
            query=query,
            n_results=5
        ))
        
        # Получаем оптимальный контекст
        return self.compressor.get_optimal_context(
            query=query,
            recent_messages=self.context_window.messages[-20:],  # последние 20
            vector_memories=memories,
            max_tokens=max_tokens
        )
    
    async def create_summary(self, chunk_size: int = 50) -> Optional[Summary]:
        """
        Создать суммаризацию последних сообщений
        """
        if not self.summarizer or len(self.context_window.messages) < chunk_size:
            return None
        
        # Берём последние сообщения
        messages = self.context_window.messages[-chunk_size:]
        
        # Создаём чанк
        from .models import ConversationChunk
        
        chunk = ConversationChunk(
            chunk_id=f"auto_summary_{datetime.now().timestamp()}",
            conversation_id=self.conversation_id,
            messages=messages,
            start_time=messages[0]['timestamp'],
            end_time=messages[-1]['timestamp'],
            participants=list(set(m['sender'] for m in messages)),
            token_count=int(sum(len(m['content'].split()) * 1.3 for m in messages))
        )
        
        # Суммаризируем
        summary = await self.summarizer.summarize_chunk(chunk)
        
        if summary:
            self.stats["summaries_created"] += 1
            
            # Сохраняем как семантическую память
            memory = MemoryItem(
                id=f"summary_{summary.summary_id}",
                content=summary.content,
                type=MemoryType.SEMANTIC,
                importance=ImportanceLevel.HIGH,
                timestamp=datetime.now(),
                tags=["summary", "auto_generated"],
                participants=chunk.participants,
                metadata={
                    "summary_id": summary.summary_id,
                    "key_points": summary.key_points,
                    "decisions": summary.decisions
                }
            )
            
            await self.transfer_to_long_term(memory)
        
        return summary
    
    async def _maintenance_loop(self):
        """Фоновое обслуживание памяти"""
        while self._running:
            await asyncio.sleep(300)  # каждые 5 минут
            
            # Очищаем старые краткосрочные воспоминания
            self.short_term = [m for m in self.short_term if not m.is_expired()]
            
            # Проверяем, не пора ли создать сводку
            if len(self.context_window.messages) > 100:
                await self.create_summary(chunk_size=50)
            
            # Обновляем статистику
            self.stats["short_term_items"] = len(self.short_term)
    
    def _extract_tags(self, content: str) -> List[str]:
        """Извлечь теги из сообщения"""
        tags = []
        
        # Хэштеги
        import re
        hashtags = re.findall(r'#(\w+)', content)
        tags.extend(hashtags)
        
        # Ключевые слова
        important_words = ['важно', 'срочно', 'решение', 'итог']
        for word in important_words:
            if word in content.lower():
                tags.append(word)
        
        return tags
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "context_window": {
                "messages": len(self.context_window.messages),
                "tokens": self.context_window.current_tokens,
                "summaries": len(self.context_window.summaries)
            },
            "vector_store_stats": self.vector_store.get_stats() if self.vector_store else None,
            "summarizer_stats": self.summarizer.get_stats() if self.summarizer else None
        }
    
    def get_memory_summary(self) -> str:
        """Получить сводку по памяти"""
        lines = [
            f"📊 **Сводка памяти**",
            f"Краткосрочная память: {len(self.short_term)} элементов",
            f"Долгосрочная память: {self.stats['long_term_items']} элементов",
            f"Контекстное окно: {len(self.context_window.messages)} сообщений / {self.context_window.current_tokens} токенов",
            f"Создано сводок: {self.stats['summaries_created']}",
            f"Компрессий контекста: {self.stats['context_compressions']}"
        ]
        
        if self.context_window.summaries:
            lines.append("\n📝 Последние сводки:")
            for s in self.context_window.summaries[-3:]:
                lines.append(f"  • {s.key_points[0] if s.key_points else s.content[:50]}...")
        
        return "\n".join(lines)
