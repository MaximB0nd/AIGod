"""
Агент для суммаризации контекста
"""
import asyncio
import json
import re
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
import tiktoken

from .models import Summary, ConversationChunk, MemoryItem, MemoryType, ImportanceLevel

class ContextSummarizer:
    """
    Суммаризатор контекста с использованием AI-агента
    """
    
    def __init__(self, 
                 chat_service,
                 summarizer_agent_name: str = "context_summarizer",
                 max_tokens_per_summary: int = 500,
                 compression_target: float = 0.3):  # сжимать до 30%
        
        self.chat_service = chat_service
        self.summarizer_agent_name = summarizer_agent_name
        self.max_tokens_per_summary = max_tokens_per_summary
        self.compression_target = compression_target
        
        # Токенизатор для подсчёта
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
        
        # Очередь на суммаризацию
        self.summary_queue = asyncio.Queue()
        
        # История суммаризаций
        self.summaries: Dict[str, Summary] = {}
        
        # Статистика
        self.stats = {
            "total_summaries": 0,
            "total_tokens_processed": 0,
            "total_tokens_saved": 0,
            "api_calls": 0,
            "errors": 0
        }
        
        # Колбэки
        self.callbacks: List[Callable] = []
        
        # Запускаем воркер
        self._worker_task = None
        self._running = False
    
    def on_summary(self, callback: Callable[[Summary], None]):
        """Подписаться на результаты суммаризации"""
        self.callbacks.append(callback)
    
    async def start(self):
        """Запустить суммаризатор"""
        if not self._worker_task:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        """Остановить суммаризатор"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
    
    def count_tokens(self, text: str) -> int:
        """Подсчитать количество токенов"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Грубая оценка
        return len(text.split()) * 1.3
    
    async def summarize_chunk(self, 
                              chunk: ConversationChunk,
                              previous_summary: Optional[Summary] = None) -> Optional[Summary]:
        """
        Суммаризировать чанк разговора
        """
        # Формируем промпт
        prompt = self._build_summary_prompt(chunk, previous_summary)
        
        try:
            self.stats["api_calls"] += 1
            
            # Вызываем агента
            response = await self.chat_service(
                agent_name=self.summarizer_agent_name,
                session_id=f"summarize_{chunk.conversation_id}",
                prompt=prompt
            )
            
            # Парсим результат
            summary_data = self._parse_summary_response(response)
            
            if summary_data:
                # Создаём объект суммаризации
                summary = Summary(
                    summary_id=f"summary_{datetime.now().timestamp()}",
                    original_chunks=[chunk.chunk_id],
                    content=summary_data.get("content", ""),
                    created_at=datetime.now(),
                    token_count=self.count_tokens(summary_data.get("content", "")),
                    key_points=summary_data.get("key_points", []),
                    decisions=summary_data.get("decisions", []),
                    action_items=summary_data.get("action_items", []),
                    compression_ratio=chunk.token_count / max(1, self.count_tokens(summary_data.get("content", ""))),
                    quality_score=summary_data.get("quality_score", 0.7)
                )
                
                # Сохраняем
                self.summaries[summary.summary_id] = summary
                self.stats["total_summaries"] += 1
                self.stats["total_tokens_processed"] += chunk.token_count
                self.stats["total_tokens_saved"] += chunk.token_count - summary.token_count
                
                # Вызываем колбэки
                for callback in self.callbacks:
                    try:
                        callback(summary)
                    except Exception as e:
                        print(f"Error in callback: {e}")
                
                return summary
            
        except Exception as e:
            print(f"Error in summarization: {e}")
            self.stats["errors"] += 1
        
        return None
    
    async def summarize_hierarchical(self, 
                                    chunks: List[ConversationChunk],
                                    level: int = 0) -> List[Summary]:
        """
        Иерархическая суммаризация (суммаризация суммаризаций)
        """
        if len(chunks) == 1:
            # Базовый случай
            summary = await self.summarize_chunk(chunks[0])
            return [summary] if summary else []
        
        # Рекурсивно суммаризируем половины
        mid = len(chunks) // 2
        left_summaries = await self.summarize_hierarchical(chunks[:mid], level + 1)
        right_summaries = await self.summarize_hierarchical(chunks[mid:], level + 1)
        
        # Если есть что суммаризировать на этом уровне
        all_summaries = left_summaries + right_summaries
        
        if len(all_summaries) > 1 and level < 3:  # максимум 3 уровня
            # Объединяем суммаризации
            combined_content = "\n\n".join([s.content for s in all_summaries])
            
            combined_chunk = ConversationChunk(
                chunk_id=f"level_{level}_{datetime.now().timestamp()}",
                conversation_id=chunks[0].conversation_id,
                messages=[],  # не храним оригиналы
                start_time=chunks[0].start_time,
                end_time=chunks[-1].end_time,
                participants=list(set(sum(p.participants for p in chunks))),
                token_count=self.count_tokens(combined_content)
            )
            
            # Создаём промпт для суммаризации суммаризаций
            prompt = f"""
            Ты выполняешь иерархическую суммаризацию разговора.
            
            Ниже представлены суммаризации частей разговора:
            
            {combined_content}
            
            Создай краткую сводку, объединяющую все эти части.
            Выдели основные темы, решения и действия.
            """
            
            try:
                response = await self.chat_service(
                    agent_name=self.summarizer_agent_name,
                    session_id=f"hierarchical_{chunks[0].conversation_id}",
                    prompt=prompt
                )
                
                summary_data = self._parse_summary_response(response)
                
                if summary_data:
                    parent_summary = Summary(
                        summary_id=f"hier_summary_{datetime.now().timestamp()}",
                        original_chunks=[s.summary_id for s in all_summaries],
                        content=summary_data.get("content", ""),
                        created_at=datetime.now(),
                        token_count=self.count_tokens(summary_data.get("content", "")),
                        key_points=summary_data.get("key_points", []),
                        decisions=summary_data.get("decisions", []),
                        action_items=summary_data.get("action_items", [])
                    )
                    
                    # Устанавливаем связи
                    for s in all_summaries:
                        s.parent_summary = parent_summary.summary_id
                        parent_summary.child_summaries.append(s.summary_id)
                    
                    self.summaries[parent_summary.summary_id] = parent_summary
                    return [parent_summary]
                
            except Exception as e:
                print(f"Error in hierarchical summarization: {e}")
        
        return all_summaries
    
    def _build_summary_prompt(self, 
                             chunk: ConversationChunk,
                             previous_summary: Optional[Summary] = None) -> str:
        """Сформировать промпт для суммаризации"""
        
        # Формируем текст разговора
        conversation_text = "\n".join([
            f"{msg['sender']}: {msg['content']}" 
            for msg in chunk.messages
        ])
        
        previous = ""
        if previous_summary:
            previous = f"\nПредыдущая сводка:\n{previous_summary.content}\n"
        
        return f"""
Ты выполняешь суммаризацию фрагмента разговора между {', '.join(chunk.participants)}.

{previous}
Фрагмент для суммаризации:
{conversation_text}

Создай краткую, информативную сводку этого фрагмента.
Следуй структуре:

1. **Основная тема**: 1-2 предложения о чём разговор
2. **Ключевые моменты**: список важных мыслей
3. **Принятые решения**: если были
4. **Действия**: что нужно сделать
5. **Эмоциональная атмосфера**: кратко

Важно:
- Сохрани все важные факты
- Уложись в {self.max_tokens_per_summary} токенов
- Будь объективен

Ответь в формате JSON:
{{
    "content": "полная сводка",
    "key_points": ["пункт 1", "пункт 2"],
    "decisions": ["решение 1"],
    "action_items": ["действие 1"],
    "quality_score": 0.8
}}
"""
    
    def _parse_summary_response(self, response: str) -> Optional[Dict]:
        """Распарсить ответ агента"""
        try:
            # Ищем JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Если нет JSON, пытаемся извлечь структуру из текста
            return self._extract_structure_from_text(response)
            
        except Exception as e:
            print(f"Error parsing summary: {e}")
            return None
    
    def _extract_structure_from_text(self, text: str) -> Dict:
        """Извлечь структуру из текстового ответа"""
        lines = text.split('\n')
        
        content = []
        key_points = []
        decisions = []
        actions = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "**Основная тема**" in line or "1." in line and "тема" in line.lower():
                current_section = "content"
            elif "**Ключевые моменты**" in line or "2." in line:
                current_section = "key_points"
            elif "**Принятые решения**" in line or "3." in line:
                current_section = "decisions"
            elif "**Действия**" in line or "4." in line:
                current_section = "actions"
            elif current_section == "content":
                content.append(line)
            elif current_section == "key_points" and line.startswith('-'):
                key_points.append(line[1:].strip())
            elif current_section == "decisions" and line.startswith('-'):
                decisions.append(line[1:].strip())
            elif current_section == "actions" and line.startswith('-'):
                actions.append(line[1:].strip())
        
        return {
            "content": " ".join(content),
            "key_points": key_points,
            "decisions": decisions,
            "action_items": actions,
            "quality_score": 0.6
        }
    
    async def _worker_loop(self):
        """Воркер для обработки очереди"""
        while self._running:
            try:
                # Получаем задачу из очереди
                chunk = await asyncio.wait_for(
                    self.summary_queue.get(), 
                    timeout=1.0
                )
                
                # Суммаризируем
                summary = await self.summarize_chunk(chunk)
                
                if summary:
                    # Здесь можно сохранить или отправить куда-то
                    pass
                
            except asyncio.TimeoutError:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in summarizer worker: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(1)
    
    def get_summary(self, summary_id: str) -> Optional[Summary]:
        """Получить суммаризацию по ID"""
        return self.summaries.get(summary_id)
    
    def get_summaries_for_conversation(self, conversation_id: str) -> List[Summary]:
        """Получить все суммаризации для разговора"""
        return [s for s in self.summaries.values() 
                if conversation_id in s.original_chunks or
                any(conversation_id in c for c in s.original_chunks)]
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "total_summaries_stored": len(self.summaries),
            "queue_size": self.summary_queue.qsize(),
            "avg_compression": self.stats["total_tokens_saved"] / max(1, self.stats["total_tokens_processed"])
        }
