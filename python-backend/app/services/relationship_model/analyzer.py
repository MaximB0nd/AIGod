"""
Агент-аналитик для оценки влияния сообщений на отношения
"""
import asyncio
import json
import re
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import deque

from .models import AnalysisResult

class RelationshipAnalyzer:
    """
    Анализирует сообщения и определяет их влияние на отношения
    """
    
    def __init__(self, 
                 chat_service,  # любой chat_service с интерфейсом __call__
                 analyzer_agent_name: str = "relationship_analyzer",
                 influence_coefficient: float = 0.3,
                 batch_size: int = 5):
        
        self.chat_service = chat_service
        self.analyzer_agent_name = analyzer_agent_name
        self.influence_coefficient = influence_coefficient
        self.batch_size = batch_size
        
        # Очередь сообщений на анализ
        self.analysis_queue = asyncio.Queue()
        
        # История анализов
        self.analysis_history = deque(maxlen=1000)
        
        # Статистика
        self.stats = {
            "total_analyzed": 0,
            "api_calls": 0,
            "errors": 0,
            "avg_processing_time": 0
        }
        
        # Колбэки при получении результата
        self.callbacks: List[Callable] = []
        
        # Запускаем воркер
        self._worker_task = None
        self._running = False
    
    def on_analysis(self, callback: Callable[[AnalysisResult], None]):
        """Подписаться на результаты анализа"""
        self.callbacks.append(callback)
    
    async def start(self):
        """Запустить анализатор"""
        if not self._worker_task:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
    
    async def stop(self):
        """Остановить анализатор"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
    
    async def analyze_message(self, 
                             message: str,
                             sender: str,
                             participants: List[str],
                             context: Optional[List[str]] = None,
                             message_id: Optional[str] = None) -> Optional[AnalysisResult]:
        """
        Отправить сообщение на анализ (асинхронно)
        """
        msg_id = message_id or f"{sender}_{datetime.now().timestamp()}"
        
        # Создаём будущий результат
        future = asyncio.Future()
        
        await self.analysis_queue.put({
            "message": message,
            "sender": sender,
            "participants": participants,
            "context": context or [],
            "message_id": msg_id,
            "future": future
        })
        
        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            self.stats["errors"] += 1
            return None
    
    async def analyze_message_sync(self, *args, **kwargs) -> Optional[AnalysisResult]:
        """
        Синхронный анализ (ждёт результата)
        """
        return await self.analyze_message(*args, **kwargs)
    
    async def _worker_loop(self):
        """Воркер для пакетной обработки"""
        while self._running:
            try:
                # Собираем батч
                batch = []
                for _ in range(self.batch_size):
                    try:
                        item = await asyncio.wait_for(
                            self.analysis_queue.get(), 
                            timeout=0.1
                        )
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break
                
                if batch:
                    await self._process_batch(batch)
                else:
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in analyzer worker: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: List[Dict]):
        """Обработать батч сообщений"""
        import time
        
        for item in batch:
            start_time = time.time()
            
            try:
                # Создаём промпт для анализа
                prompt = self._build_analysis_prompt(
                    message=item["message"],
                    sender=item["sender"],
                    participants=item["participants"],
                    context=item["context"]
                )
                
                # Вызываем агента
                self.stats["api_calls"] += 1
                response = await self.chat_service(
                    agent_name=self.analyzer_agent_name,
                    session_id="relationship_analysis",
                    prompt=prompt
                )
                
                # Парсим результат
                result = self._parse_response(response, item)
                
                if result:
                    # Сохраняем
                    self.analysis_history.append(result)
                    self.stats["total_analyzed"] += 1
                    
                    # Вызываем колбэки
                    for callback in self.callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                    
                    # Возвращаем результат
                    item["future"].set_result(result)
                else:
                    item["future"].set_result(None)
                
            except Exception as e:
                print(f"Error processing item: {e}")
                self.stats["errors"] += 1
                item["future"].set_result(None)
            
            # Обновляем статистику времени
            process_time = time.time() - start_time
            self.stats["avg_processing_time"] = (
                self.stats["avg_processing_time"] * 0.9 + process_time * 0.1
            )
    
    def _build_analysis_prompt(self, message: str, sender: str, 
                               participants: List[str], context: List[str]) -> str:
        """Сформировать промпт для анализа"""
        
        context_text = ""
        if context:
            context_text = "\n".join([
                "Контекст предыдущих сообщений:",
                *[f"  {msg}" for msg in context[-3:]]
            ])
        
        return f"""
Ты аналитик отношений. Проанализируй сообщение и определи, как оно повлияет на отношения.

{context_text}

Сообщение от {sender}:
"{message}"

Участники: {', '.join(participants)}

Оцени влияние на отношения {sender} с каждым участником.
Используй шкалу от -1 (сильно портит) до 1 (сильно улучшает).

Ответь ТОЛЬКО в формате JSON:
{{
    "impacts": {{
        "имя_участника1": число,
        "имя_участника2": число
    }},
    "sentiment": число (общая тональность -1 до 1),
    "emotions": {{
        "anger": 0-1,
        "joy": 0-1,
        "sadness": 0-1,
        "trust": 0-1
    }},
    "reason": "краткое объяснение"
}}
"""
    
    def _parse_response(self, response: str, item: Dict) -> Optional[AnalysisResult]:
        """Распарсить ответ агента"""
        try:
            # Ищем JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            return AnalysisResult(
                message_id=item["message_id"],
                sender=item["sender"],
                content=item["message"],
                timestamp=datetime.now(),
                impacts=data.get("impacts", {}),
                sentiment=data.get("sentiment", 0),
                emotions=data.get("emotions", {}),
                reason=data.get("reason", "Анализ не удался"),
                metadata={
                    "participants": item["participants"],
                    "context_size": len(item["context"])
                }
            )
        except Exception as e:
            print(f"Error parsing response: {e}")
            return None
    
    def get_recent_analyses(self, limit: int = 10) -> List[AnalysisResult]:
        """Получить последние анализы"""
        return list(self.analysis_history)[-limit:]
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "queue_size": self.analysis_queue.qsize(),
            "history_size": len(self.analysis_history)
        }
