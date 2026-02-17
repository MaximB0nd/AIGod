import asyncio
from typing import List, Optional, Callable, Awaitable
from .context import ConversationContext
from .base_strategy import BaseStrategy
from .events import UserMessageEvent
from .message import Message
from .message_type import MessageType

class OrchestrationClient:
    """
    Главный клиент оркестрации.
    Управляет стратегией, обрабатывает сообщения и контролирует поток выполнения.
    """
    
    def __init__(self, agents: List[str], chat_service: Callable[..., Awaitable[str]], room_id: Optional[int] = None):
        self.agents = agents
        self.chat_service = chat_service
        self.room_id = room_id
        self.context = ConversationContext(participants=agents.copy())
        self.strategy: Optional[BaseStrategy] = None
        self.running = False
        self.message_queue = asyncio.Queue()
        self.user_message_queue: asyncio.Queue = asyncio.Queue()  # UserMessageEvent | str (legacy)
        self.tick_interval = 1.0
        self.max_ticks: Optional[int] = None
        self.current_tick = 0
        self._on_message_callback: Optional[Callable[[Message], Awaitable[None]]] = None
    
    def set_strategy(self, strategy: BaseStrategy):
        """Установка стратегии оркестрации"""
        self.strategy = strategy
        strategy.context = self.context
        strategy.chat_service = self.chat_service  # Передаем сервис в стратегию
    
    def on_message(self, callback: Callable[[Message], Awaitable[None]]):
        """Установка колбэка для обработки сообщений"""
        self._on_message_callback = callback
    
    async def start(self, max_ticks: Optional[int] = None):
        """Запуск оркестрации"""
        if not self.strategy:
            raise ValueError("Orchestration strategy not set")
        
        self.running = True
        self.max_ticks = max_ticks
        self.current_tick = 0
        
        await self.strategy.on_start()
        
        await asyncio.gather(
            self._process_user_messages(),
            self._process_message_queue(),
            self._tick_loop(),
            return_exceptions=True
        )
    
    async def stop(self):
        """Остановка оркестрации"""
        self.running = False
        if self.strategy:
            await self.strategy.on_stop()
    
    async def send_user_message(self, message: str, sender: str = "user"):
        """Отправка сообщения от пользователя в очередь оркестрации."""
        room_id = self.room_id or 0
        event = UserMessageEvent(room_id=room_id, text=message, sender=sender)
        await self.user_message_queue.put(event)

    async def enqueue_user_message(self, room_id: int, text: str, sender: str = "user"):
        """Явная постановка сообщения пользователя в очередь (для room-level endpoint)."""
        event = UserMessageEvent(room_id=room_id, text=text, sender=sender)
        await self.user_message_queue.put(event)
    
    async def _tick_loop(self):
        """Основной цикл тиков"""
        while self.running:
            try:
                if self.strategy and self.strategy.should_stop():
                    await self.stop()
                    break
                
                if self.max_ticks and self.current_tick >= self.max_ticks:
                    await self.stop()
                    break
                
                messages = await self.strategy.tick(self.agents)
                if messages:
                    for msg in messages:
                        self.context.add_message(msg)
                        await self.message_queue.put(msg)
                
                self.current_tick += 1
                await asyncio.sleep(self.tick_interval)
                
            except Exception as e:
                print(f"Error in tick loop: {e}")
                await asyncio.sleep(self.tick_interval)
    
    async def _process_user_messages(self):
        """Обработка сообщений от пользователя (UserMessageEvent или str для обратной совместимости)."""
        while self.running:
            try:
                item = await self.user_message_queue.get()
                text = item.text if isinstance(item, UserMessageEvent) else item
                if self.strategy:
                    messages = await self.strategy.handle_user_message(text)
                    for msg in messages:
                        self.context.add_message(msg)
                        await self.message_queue.put(msg)
                self.user_message_queue.task_done()
            except Exception as e:
                print(f"Error processing user message: {e}")
    
    async def _process_message_queue(self):
        """Обработка очереди сообщений"""
        while self.running:
            try:
                message = await self.message_queue.get()
                
                # Вызываем колбэк если установлен
                if self._on_message_callback:
                    await self._on_message_callback(message)
                else:
                    # Стандартный вывод
                    self._default_message_handler(message)
                
                self.message_queue.task_done()
            except Exception as e:
                print(f"Error processing message queue: {e}")
    
    def _default_message_handler(self, message: Message):
        """Стандартный обработчик сообщений"""
        timestamp = message.timestamp.strftime("%H:%M:%S")
        sender_icon = {
            MessageType.USER: "👤",
            MessageType.AGENT: "🤖",
            MessageType.SYSTEM: "⚙️",
            MessageType.NARRATOR: "📖",
            MessageType.CONTEXT_UPDATE: "🔄",
            MessageType.SUMMARIZED: "📝"
        }.get(message.type, "📌")
        
        print(f"{timestamp} {sender_icon} [{message.type}] {message.sender}: {message.content}")
    
    def get_statistics(self) -> dict:
        """Получить статистику работы"""
        return {
            "context": self.context.get_statistics(),
            "strategy": self.strategy.get_config() if self.strategy else None,
            "running": self.running,
            "ticks": self.current_tick,
            "queue_sizes": {
                "messages": self.message_queue.qsize(),
                "user": self.user_message_queue.qsize()
            }
        }
