from typing import List, Optional
from datetime import datetime

from ..base_strategy import BaseStrategy
from ..context import ConversationContext
from ..message import Message
from ..message_type import MessageType

class CircularStrategy(BaseStrategy):
    """
    Стратегия циркулярной оркестрации:
    - Агенты общаются по кругу
    - Пользователь может вмешаться в любой момент
    - При вмешательстве пользователя круг начинается заново
    """
    
    def __init__(self, context: ConversationContext,
                 start_agent_index: int = 0,
                 include_system_messages: bool = True,
                 max_rounds: int = 5):
        super().__init__(context)
        self.current_agent_index = start_agent_index
        self.include_system_messages = include_system_messages
        self.max_rounds = max_rounds  # Защита от бесконечного цикла
        self.round_count = 1
        self.user_interrupted = False
        self.last_user_message: Optional[str] = None
        self.waiting_for_user_response = False
    
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        if not agents:
            return None
        
        # Если есть новое сообщение от пользователя
        if self.user_interrupted and self.last_user_message:
            self.user_interrupted = False
            self.waiting_for_user_response = True
            self.current_agent_index = 0
            self.round_count = 1
            
            # Отправляем сообщение пользователя первому агенту
            response = await self.chat_service(
                agents[0],
                "circular_session",
                self.last_user_message,
                context=self.context
            )
            
            messages = [
                Message(
                    content=self.last_user_message,
                    type=MessageType.USER,
                    sender="Пользователь",
                    timestamp=datetime.now(),
                    metadata={"type": "user_input"}
                ),
                Message(
                    content=response,
                    type=MessageType.AGENT,
                    sender=agents[0],
                    timestamp=datetime.now(),
                    metadata={
                        "agent_index": 0, 
                        "round": self.round_count,
                        "response_to_user": True
                    }
                )
            ]
            
            self.current_agent_index = 1
            self.waiting_for_user_response = False
            return messages
        
        # Если ждем ответ от пользователя, пропускаем тик
        if self.waiting_for_user_response:
            return None
        
        # Обычный цикл между агентами
        if not self.context.history:
            return None
        
        # Проверяем, было ли последнее сообщение от пользователя
        last_message = self.context.get_last_message()
        if not last_message:
            return None
        
        # Если последнее сообщение от пользователя, начинаем новый круг
        if last_message.type == MessageType.USER:
            self.current_agent_index = 0
            self.round_count = 1
        
        current_agent = agents[self.current_agent_index]
        
        # Формируем контекст для агента
        context_messages = self.context.get_recent_messages(3)
        context_text = "\n".join([f"{m.sender}: {m.content}" for m in context_messages])
        
        prompt = self._build_agent_prompt(current_agent, context_text, last_message)
        
        response = await self.chat_service(
            current_agent,
            "circular_session",
            prompt,
            context=self.context
        )
        
        message = Message(
            content=response,
            type=MessageType.AGENT,
            sender=current_agent,
            timestamp=datetime.now(),
            metadata={
                "agent_index": self.current_agent_index,
                "round": self.round_count,
                "responding_to": last_message.sender
            }
        )
        
        # Переходим к следующему агенту
        self.current_agent_index = (self.current_agent_index + 1) % len(agents)
        
        # Если завершили круг
        if self.current_agent_index == 0:
            self.round_count += 1
            if self.include_system_messages:
                system_msg = Message(
                    content="=== Обсуждение продолжается ===",
                    type=MessageType.SYSTEM,
                    sender="Система",
                    timestamp=datetime.now(),
                    metadata={"cycle": self.round_count}
                )
                return [message, system_msg]
        
        return [message]
    
    async def handle_user_message(self, message: str) -> List[Message]:
        """Обработка сообщения пользователя. Сохраняем в context — центр для всех промптов."""
        self.user_interrupted = True
        self.last_user_message = message
        self.context.current_user_message = message
        self.context.update_memory("_user_message", message)
        # Не создаем сообщение здесь, оно будет создано в tick
        return []
    
    def _build_agent_prompt(self, agent: str, context_text: str, last_message: Message) -> str:
        """Формирование промпта для агента. ЗАПРОС ПОЛЬЗОВАТЕЛЯ — в центре, чтобы агенты не игнорировали его."""
        user_msg = (
            self.context.current_user_message
            or self.last_user_message
            or self.context.get_memory("_user_message")
            or ""
        )
        memory_ctx = self.context.get_memory("_memory_context") or ""

        prompt_parts = [
            f"Ты {agent} в циркулярном разговоре. Текущий раунд: {self.round_count}.",
        ]
        if user_msg:
            prompt_parts.extend([
                "",
                "═══ ЗАПРОС ПОЛЬЗОВАТЕЛЯ (ГЛАВНЫЙ ФОКУС — НЕ ИГНОРИРУЙ) ═══",
                f"«{user_msg}»",
                "",
            ])
        if memory_ctx:
            prompt_parts.extend([
                "Релевантные воспоминания из памяти:",
                memory_ctx,
                "",
            ])
        prompt_parts.extend([
            "Обсуждение агентов:",
            context_text,
            "",
            f"Последнее сообщение от {last_message.sender}:",
            f"«{last_message.content}»",
            "",
            "Продолжи обсуждение ЗАПРОСА ПОЛЬЗОВАТЕЛЯ. Отвечай на последнее сообщение, но помни о запросе пользователя.",
        ])

        if self.context.current_topic:
            prompt_parts.insert(1, f"Тема: {self.context.current_topic}")
        return "\n".join(prompt_parts)
    
    def should_stop(self) -> bool:
        """Остановиться после max_rounds кругов (защита от зацикливания)."""
        return self.round_count > self.max_rounds
