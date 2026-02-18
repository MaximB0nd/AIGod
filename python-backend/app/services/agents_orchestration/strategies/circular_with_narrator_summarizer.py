"""
Стратегия циркулярной оркестрации с Рассказчиком и Суммаризатором в каждом чате.

Как в разговор_лог.txt:
- Агенты общаются по кругу
- 🎭 Рассказчик Нарратор — описывает сцену, действия, атмосферу (каждые N сообщений)
- 📊 Сводка Суммаризатор — структурированная сводка после каждого раунда
- Система — «=== Раунд X завершён ===»
"""
from typing import List, Optional
from datetime import datetime

from ..base_strategy import BaseStrategy
from ..context import ConversationContext
from ..message import Message
from ..message_type import MessageType


class CircularWithNarratorSummarizerStrategy(BaseStrategy):
    """
    Циркулярная оркестрация с Рассказчиком и Суммаризатором в каждом чате.
    """

    def __init__(
        self,
        context: ConversationContext,
        start_agent_index: int = 0,
        include_system_messages: bool = True,
        max_rounds: Optional[int] = None,
        narrator_interval: int = 2,
        narrator_agent_name: str = "Нарратор",
        narrator_display_name: str = "🎭 Рассказчик Нарратор",
        summarizer_agent_name: str = "Суммаризатор",
        summarizer_display_name: str = "📊 Сводка Суммаризатор",
    ):
        super().__init__(context)
        self.current_agent_index = start_agent_index
        self.include_system_messages = include_system_messages
        self.max_rounds = max_rounds  # None = бесконечная циркуляция (умная остановка)
        self.narrator_interval = narrator_interval
        self.narrator_agent_name = narrator_agent_name
        self.narrator_display_name = narrator_display_name
        self.summarizer_agent_name = summarizer_agent_name
        self.summarizer_display_name = summarizer_display_name

        self.round_count = 1
        self.user_interrupted = False
        self.last_user_message: Optional[str] = None
        self.waiting_for_user_response = False
        self.agent_messages_since_narrator = 0
        self.convergence_count = 0
        self._last_summary_hash: Optional[int] = None

    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        """Один тик: агент, или рассказчик, или суммаризатор + система."""
        discussion_agents = [
            a for a in agents
            if a not in (self.narrator_agent_name, self.summarizer_agent_name)
        ]
        if not discussion_agents:
            return None

        if self.user_interrupted and self.last_user_message:
            return await self._handle_user_interrupt(discussion_agents)

        if self.waiting_for_user_response:
            return None

        if not self.context.history:
            return None

        last_message = self.context.get_last_message()
        if not last_message:
            return None

        if last_message.type == MessageType.USER:
            self.current_agent_index = 0
            self.round_count = 1
            self.agent_messages_since_narrator = 0

        current_agent = discussion_agents[self.current_agent_index]
        context_messages = self.context.get_recent_messages(8)
        context_text = "\n".join([f"{m.sender}: {m.content}" for m in context_messages])
        prompt = self._build_agent_prompt(current_agent, context_text, last_message)

        response = await self.chat_service(
            current_agent,
            "circular_narrator_session",
            prompt,
            context=self.context,
        )

        msg = Message(
            content=response,
            type=MessageType.AGENT,
            sender=current_agent,
            timestamp=datetime.now(),
            metadata={
                "agent_index": self.current_agent_index,
                "round": self.round_count,
                "responding_to": last_message.sender,
            },
        )
        self.agent_messages_since_narrator += 1
        self.context.add_message(msg)

        messages = [msg]
        self.current_agent_index = (self.current_agent_index + 1) % len(discussion_agents)

        if self.current_agent_index == 0:
            self.round_count += 1

            if self.agent_messages_since_narrator >= self.narrator_interval:
                narrator_msg = await self._call_narrator(context_messages, response)
                if narrator_msg:
                    messages.append(narrator_msg)
                    self.context.add_message(narrator_msg)
                self.agent_messages_since_narrator = 0

            summarizer_msg = await self._call_summarizer(discussion_agents)
            if summarizer_msg:
                messages.append(summarizer_msg)

            if self.include_system_messages:
                system_msg = Message(
                    content=f"=== Раунд {self.round_count} завершён ===",
                    type=MessageType.SYSTEM,
                    sender="Система",
                    timestamp=datetime.now(),
                    metadata={"round_completed": self.round_count},
                )
                messages.append(system_msg)
        else:
            if self.agent_messages_since_narrator >= self.narrator_interval:
                narrator_msg = await self._call_narrator(context_messages, response)
                if narrator_msg:
                    messages.append(narrator_msg)
                self.agent_messages_since_narrator = 0

        return messages

    async def _handle_user_interrupt(self, discussion_agents: List[str]) -> Optional[List[Message]]:
        self.user_interrupted = False
        self.waiting_for_user_response = True
        self.current_agent_index = 0
        self.round_count = 1
        self.agent_messages_since_narrator = 0

        response = await self.chat_service(
            discussion_agents[0],
            "circular_narrator_session",
            self.last_user_message,
            context=self.context,
        )

        self.waiting_for_user_response = False
        self.current_agent_index = 1
        return [
            Message(
                content=self.last_user_message,
                type=MessageType.USER,
                sender="Пользователь",
                timestamp=datetime.now(),
                metadata={"type": "user_input"},
            ),
            Message(
                content=response,
                type=MessageType.AGENT,
                sender=discussion_agents[0],
                timestamp=datetime.now(),
                metadata={"agent_index": 0, "round": self.round_count, "response_to_user": True},
            ),
        ]

    async def _call_narrator(
        self, context_messages: List, last_response: str
    ) -> Optional[Message]:
        try:
            context_text = "\n".join(
                [f"{m.sender}: {m.content[:200]}..." if len(m.content) > 200 else f"{m.sender}: {m.content}"
                 for m in context_messages[-6:]]
            )
            prompt = f"""На основе обсуждения напиши короткий нарративный фрагмент (2-4 предложения).
Опиши сцену, атмосферу, действия персонажей. От третьего лица.

Контекст:
{context_text}

Последняя реплика:
{last_response[:300]}...

Твой нарративный фрагмент:"""
            content = await self.chat_service(
                self.narrator_agent_name,
                "narrator_session",
                prompt,
                context=self.context,
            )
            return Message(
                content=content.strip() if content else "",
                type=MessageType.NARRATOR,
                sender=self.narrator_display_name,
                timestamp=datetime.now(),
                metadata={"round": self.round_count},
            )
        except Exception:
            return None

    async def _call_summarizer(self, discussion_agents: List[str]) -> Optional[Message]:
        try:
            recent = self.context.get_recent_messages(15)
            discussion_text = "\n".join(
                [f"{m.sender}: {m.content}" for m in recent if m.type in (MessageType.AGENT, MessageType.NARRATOR)]
            )
            user_msg = (
                self.context.current_user_message
                or self.last_user_message
                or self.context.get_memory("_user_message")
                or ""
            )
            prompt = f"""Сделай структурированную сводку этого раунда обсуждения.
Запрос пользователя: {user_msg}

Обсуждение:
{discussion_text}

Формат (соблюдай):
1. **Main ideas presented:**
2. **Agreements or consensus:**
3. **Points of contention:**
4. **Questions raised:**
5. **Suggestions for next round:**"""
            content = await self.chat_service(
                self.summarizer_agent_name,
                "summarizer_session",
                prompt,
                context=self.context,
            )
            return Message(
                content=content.strip() if content else "",
                type=MessageType.SUMMARIZED,
                sender=self.summarizer_display_name,
                timestamp=datetime.now(),
                metadata={"round": self.round_count},
            )
        except Exception:
            return None

    async def handle_user_message(self, message: str) -> List[Message]:
        self.user_interrupted = True
        self.last_user_message = message
        self.context.current_user_message = message
        self.context.update_memory("_user_message", message)
        return []

    def _build_agent_prompt(self, agent: str, context_text: str, last_message: Message) -> str:
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
            prompt_parts.extend(
                [
                    "",
                    "═══ ЗАПРОС ПОЛЬЗОВАТЕЛЯ (ГЛАВНЫЙ ФОКУС — НЕ ИГНОРИРУЙ) ═══",
                    f"«{user_msg}»",
                    "",
                ]
            )
        if memory_ctx:
            prompt_parts.extend(["Релевантные воспоминания:", memory_ctx, ""])
        prompt_parts.extend(
            [
                "Обсуждение:",
                context_text,
                "",
                f"Последнее сообщение от {last_message.sender}:",
                f"«{last_message.content}»",
                "",
                "Продолжи обсуждение. Отвечай на последнее сообщение.",
            ]
        )
        if self.context.current_topic:
            prompt_parts.insert(1, f"Тема: {self.context.current_topic}")
        return "\n".join(prompt_parts)

    def should_stop(self) -> bool:
        if self.max_rounds is not None and self.round_count > self.max_rounds:
            return True
        return False
