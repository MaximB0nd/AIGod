"""
Агент-аналитик для определения эмоций в сообщениях
"""
import asyncio
import json
import re
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import deque

from .models import EmotionAnalysisResult, EmotionType

class EmotionAnalyzer:
    """
    Анализирует эмоциональную окраску сообщений
    """
    
    def __init__(self, 
                 chat_service,  # любой chat_service с интерфейсом __call__
                 analyzer_agent_name: str = "emotion_analyzer",
                 batch_size: int = 5):
        
        self.chat_service = chat_service
        self.analyzer_agent_name = analyzer_agent_name
        self.batch_size = batch_size
        
        # Очередь на анализ
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
        
        # Колбэки
        self.callbacks: List[Callable] = []
        
        # Эмоциональный словарь (для быстрого анализа без API)
        self.emotion_keywords = self._init_emotion_keywords()
        
        # Запускаем воркер
        self._worker_task = None
        self._running = False
    
    def _init_emotion_keywords(self) -> Dict[EmotionType, List[str]]:
        """Инициализировать ключевые слова для эмоций"""
        return {
            EmotionType.JOY: ["счастлив", "рад", "отлично", "прекрасно", "love", "like", "good", "great"],
            EmotionType.SADNESS: ["грустн", "печаль", "жаль", "плохо", "bad", "sad", "unhappy"],
            EmotionType.ANGER: ["зл", "сердит", "разозл", "бесит", "angry", "mad", "furious"],
            EmotionType.FEAR: ["страш", "боюсь", "опасно", "тревог", "fear", "scared", "afraid"],
            EmotionType.TRUST: ["верю", "довер", "надежн", "честн", "trust", "reliable", "honest"],
            EmotionType.DISGUST: ["против", "отврати", "гадк", "disgust", "gross", "awful"],
            EmotionType.ANTICIPATION: ["жду", "ожида", "скоро", "надеюсь", "hope", "expect", "wait"],
            EmotionType.SURPRISE: ["удиви", "вот это да", "неожидан", "surprise", "wow", "unexpected"]
        }
    
    def on_analysis(self, callback: Callable[[EmotionAnalysisResult], None]):
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
                             use_api: bool = True,
                             message_id: Optional[str] = None) -> Optional[EmotionAnalysisResult]:
        """
        Анализировать эмоции в сообщении
        """
        msg_id = message_id or f"{sender}_{datetime.now().timestamp()}"
        
        if not use_api:
            # Быстрый анализ по ключевым словам
            return self._quick_analyze(message, sender, msg_id)
        
        # Полноценный анализ через API
        future = asyncio.Future()
        
        await self.analysis_queue.put({
            "message": message,
            "sender": sender,
            "participants": participants,
            "message_id": msg_id,
            "future": future
        })
        
        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            self.stats["errors"] += 1
            return self._quick_analyze(message, sender, msg_id)
    
    def _quick_analyze(self, message: str, sender: str, message_id: str) -> EmotionAnalysisResult:
        """Быстрый анализ по ключевым словам"""
        message_lower = message.lower()
        detected = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                detected[emotion] = min(1.0, score / 3)  # нормализация
        
        if not detected:
            detected = {EmotionType.TRUST: 0.1}  # нейтральная эмоция
        
        # Определяем основную эмоцию
        primary = max(detected.items(), key=lambda x: x[1])
        
        # Считаем тональность
        positive_emotions = [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION]
        negative_emotions = [EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR, EmotionType.DISGUST]
        
        pos_sum = sum(v for e, v in detected.items() if e in positive_emotions)
        neg_sum = sum(v for e, v in detected.items() if e in negative_emotions)
        
        sentiment = (pos_sum - neg_sum) / (len(detected) or 1)
        
        return EmotionAnalysisResult(
            message_id=message_id,
            sender=sender,
            content=message,
            timestamp=datetime.now(),
            detected_emotions=detected,
            primary_emotion=primary[0],
            intensity=primary[1],
            sentiment=sentiment,
            reason="Быстрый анализ по ключевым словам"
        )
    
    async def _worker_loop(self):
        """Воркер для обработки очереди"""
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
                print(f"Error in emotion analyzer worker: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: List[Dict]):
        """Обработать батч сообщений"""
        import time
        
        for item in batch:
            start_time = time.time()
            
            try:
                # Создаём промпт
                prompt = self._build_analysis_prompt(
                    message=item["message"],
                    sender=item["sender"]
                )
                
                # Вызываем агента
                self.stats["api_calls"] += 1
                response = await self.chat_service(
                    agent_name=self.analyzer_agent_name,
                    session_id="emotion_analysis",
                    prompt=prompt
                )
                
                # Парсим результат
                result = self._parse_response(response, item)
                
                if result:
                    self.analysis_history.append(result)
                    self.stats["total_analyzed"] += 1
                    
                    for callback in self.callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                    
                    item["future"].set_result(result)
                else:
                    # Fallback на быстрый анализ
                    fallback = self._quick_analyze(
                        item["message"], 
                        item["sender"], 
                        item["message_id"]
                    )
                    item["future"].set_result(fallback)
                
            except Exception as e:
                print(f"Error processing item: {e}")
                self.stats["errors"] += 1
                fallback = self._quick_analyze(
                    item["message"], 
                    item["sender"], 
                    item["message_id"]
                )
                item["future"].set_result(fallback)
            
            # Статистика времени
            process_time = time.time() - start_time
            self.stats["avg_processing_time"] = (
                self.stats["avg_processing_time"] * 0.9 + process_time * 0.1
            )
    
    def _build_analysis_prompt(self, message: str, sender: str) -> str:
        """Сформировать промпт для анализа эмоций"""
        return f"""
Ты эмоциональный аналитик. Определи эмоции в сообщении.

Сообщение от {sender}:
"{message}"

Определи:
1. Какие эмоции присутствуют (joy, sadness, anger, fear, trust, disgust, anticipation, surprise)
2. Интенсивность каждой эмоции от 0 до 1
3. Основная эмоция
4. Общая тональность от -1 до 1
5. Краткое объяснение

Ответь ТОЛЬКО в формате JSON:
{{
    "emotions": {{
        "joy": число,
        "sadness": число,
        "anger": число,
        "fear": число,
        "trust": число,
        "disgust": число,
        "anticipation": число,
        "surprise": число
    }},
    "primary_emotion": "название",
    "intensity": число,
    "sentiment": число,
    "reason": "объяснение"
}}
"""
    
    def _parse_response(self, response: str, item: Dict) -> Optional[EmotionAnalysisResult]:
        """Распарсить ответ агента"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            # Преобразуем строки в EmotionType
            emotions = {}
            for e_str, value in data.get("emotions", {}).items():
                try:
                    emotion_type = EmotionType(e_str.lower())
                    emotions[emotion_type] = float(value)
                except ValueError:
                    continue
            
            primary_str = data.get("primary_emotion", "").lower()
            try:
                primary = EmotionType(primary_str)
            except ValueError:
                primary = list(emotions.keys())[0] if emotions else EmotionType.TRUST
            
            return EmotionAnalysisResult(
                message_id=item["message_id"],
                sender=item["sender"],
                content=item["message"],
                timestamp=datetime.now(),
                detected_emotions=emotions,
                primary_emotion=primary,
                intensity=float(data.get("intensity", 0.5)),
                sentiment=float(data.get("sentiment", 0)),
                reason=data.get("reason", "Анализ выполнен")
            )
        except Exception as e:
            print(f"Error parsing emotion response: {e}")
            return None
    
    def get_recent_analyses(self, limit: int = 10) -> List[EmotionAnalysisResult]:
        """Получить последние анализы"""
        return list(self.analysis_history)[-limit:]
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "queue_size": self.analysis_queue.qsize(),
            "history_size": len(self.analysis_history)
        }
