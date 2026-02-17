"""
Тесты для модуля оркестрации агентов.
Проверяют OrchestrationClient, CircularStrategy и связь с async chat_service.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.agents_orchestration import (
    ConversationContext,
    Message,
    MessageType,
    OrchestrationClient,
)
from app.services.agents_orchestration.strategies import CircularStrategy


@pytest.fixture
def mock_chat_service():
    """Асинхронный chat_service для стратегий (agent_name, session_id, prompt, context)."""
    async def _chat(agent_name: str, session_id: str, prompt: str, context=None):
        return f"[{agent_name}] ответ на: {prompt[:30]}..."

    return AsyncMock(side_effect=_chat)


@pytest.fixture
def agents():
    return ["Копатыч", "Гермиона", "Билл"]


class TestConversationContext:
    """Проверка ConversationContext."""

    def test_add_and_get_recent_messages(self):
        ctx = ConversationContext(participants=["A", "B"])
        from datetime import datetime

        for i in range(5):
            ctx.add_message(
                Message(content=f"msg{i}", type=MessageType.AGENT, sender="A", timestamp=datetime.now())
            )
        recent = ctx.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[-1].content == "msg4"

    def test_get_last_message(self):
        ctx = ConversationContext()
        from datetime import datetime

        m = Message(content="last", type=MessageType.USER, sender="user", timestamp=datetime.now())
        ctx.add_message(m)
        assert ctx.get_last_message().content == "last"


class TestCircularStrategy:
    """Проверка CircularStrategy с моком chat_service."""

    @pytest.mark.asyncio
    async def test_handle_user_message_sets_interruption(self):
        ctx = ConversationContext(participants=["Агент1"])
        strategy = CircularStrategy(ctx)
        strategy.chat_service = AsyncMock(return_value="ответ")

        result = await strategy.handle_user_message("Привет!")

        assert strategy.user_interrupted is True
        assert strategy.last_user_message == "Привет!"
        assert result == []

    @pytest.mark.asyncio
    async def test_tick_with_user_message_calls_chat_service(self, mock_chat_service, agents):
        ctx = ConversationContext(participants=agents)
        strategy = CircularStrategy(ctx)
        strategy.chat_service = mock_chat_service
        strategy.user_interrupted = True
        strategy.last_user_message = "Как дела?"

        messages = await strategy.tick(agents)

        mock_chat_service.assert_called_once()
        call = mock_chat_service.call_args
        assert call[0][0] == agents[0]
        assert call[0][2] == "Как дела?"
        assert len(messages) == 2
        assert messages[0].type == MessageType.USER
        assert messages[0].content == "Как дела?"
        assert messages[1].type == MessageType.AGENT
        assert messages[1].sender == agents[0]

    @pytest.mark.asyncio
    async def test_tick_with_agent_context_continues_cycle(self, mock_chat_service, agents):
        ctx = ConversationContext(participants=agents)
        from datetime import datetime

        ctx.add_message(
            Message(
                content="Привет!",
                type=MessageType.AGENT,
                sender=agents[0],
                timestamp=datetime.now(),
            )
        )
        strategy = CircularStrategy(ctx, start_agent_index=1)
        strategy.chat_service = mock_chat_service

        messages = await strategy.tick(agents)

        assert messages is not None
        assert len(messages) >= 1
        assert messages[0].type == MessageType.AGENT
        assert messages[0].sender == agents[1]


class TestOrchestrationClient:
    """Проверка OrchestrationClient."""

    def test_set_strategy_injects_chat_service(self, mock_chat_service, agents):
        client = OrchestrationClient(agents, mock_chat_service)
        ctx = ConversationContext(participants=agents)
        strategy = CircularStrategy(ctx)

        client.set_strategy(strategy)

        assert strategy.chat_service is mock_chat_service
        assert client.strategy is strategy

    @pytest.mark.asyncio
    async def test_send_user_message_queues_message(self, mock_chat_service, agents):
        client = OrchestrationClient(agents, mock_chat_service)
        client.set_strategy(CircularStrategy(client.context))
        received = []

        async def capture(msg: Message):
            received.append(msg)

        client.on_message(capture)
        await client.send_user_message("Тест")

        assert client.user_message_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_start_requires_strategy(self, mock_chat_service, agents):
        """start() без стратегии вызывает ValueError."""
        client = OrchestrationClient(agents, mock_chat_service)

        with pytest.raises(ValueError, match="strategy not set"):
            await client.start(max_ticks=1)


class TestOrchestrationWithChatServiceAdapter:
    """Связь оркестрации с адаптером chat_service (как в examples/usage)."""

    @pytest.mark.asyncio
    async def test_circular_strategy_flow_with_mock_adapter(self, agents):
        """Полный цикл: пользователь -> агент -> агент с мок-адаптером."""
        calls = []

        async def mock_adapter(agent_name: str, session_id: str, prompt: str, context=None):
            calls.append({"agent": agent_name, "prompt": prompt[:50]})
            return f"Ответ от {agent_name}"

        ctx = ConversationContext(participants=agents)
        strategy = CircularStrategy(ctx)
        strategy.chat_service = mock_adapter

        # Симуляция сообщения пользователя
        await strategy.handle_user_message("Начнём разговор")
        msgs = await strategy.tick(agents)

        assert len(msgs) == 2
        assert msgs[0].content == "Начнём разговор"
        assert msgs[1].content == "Ответ от Копатыч"
        assert len(calls) == 1
        assert calls[0]["agent"] == "Копатыч"
