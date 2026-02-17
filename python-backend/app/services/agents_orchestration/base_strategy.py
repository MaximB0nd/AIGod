from abc import ABC, abstractmethod
from typing import List, Optional
from .context import ConversationContext
from .message import Message

class BaseStrategy(ABC):
    """
    Базовый класс для всех стратегий оркестрации.
    Определяет интерфейс, который должны реализовать все стратегии.
    """
    
    def __init__(self, context: ConversationContext):
        self.context = context
        self.name = self.__class__.__name__
        self._chat_service = None  # Будет установлен клиентом
    
    @property
    def chat_service(self):
        """Доступ к chat service (устанавливается клиентом)"""
        if self._chat_service is None:
            raise RuntimeError("Chat service not set. This strategy is not attached to a client.")
        return self._chat_service
    
    @chat_service.setter
    def chat_service(self, value):
        self._chat_service = value
    
    @abstractmethod
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        """
        Выполняется каждый тик.
        Должен возвращать список сообщений или None.
        """
        pass
    
    @abstractmethod
    async def handle_user_message(self, message: str) -> List[Message]:
        """
        Обработка сообщения от пользователя.
        Должна возвращать список сообщений для добавления в контекст.
        """
        pass
    
    async def on_start(self):
        """Вызывается при старте стратегии"""
        pass
    
    async def on_stop(self):
        """Вызывается при остановке стратегии"""
        pass
    
    def should_stop(self) -> bool:
        """Проверка, нужно ли остановить стратегию"""
        return False
    
    def get_config(self) -> dict:
        """Получить конфигурацию стратегии"""
        return {
            "name": self.name,
            "context_size": len(self.context.history),
            "participants": self.context.participants
        }
