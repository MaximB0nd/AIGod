"""
Тесты цепочки модулей yandex_client: ChatService -> CharacterAgent -> YandexAgentClient.
С моками YandexAgentClient, чтобы проверить связь без вызова реального API.
"""
from unittest.mock import MagicMock, patch

import pytest


class TestChatServiceChain:
    """Проверка: ChatService вызывает CharacterAgent, тот — YandexAgentClient.send_message."""

    def test_chat_service_process_message_delegates_to_character_agent(self):
        """ChatService.process_message вызывает agent_client.send_message через CharacterAgent."""
        from app.services.yandex_client.chat_service import ChatService

        mock_client = MagicMock()
        mock_client.send_message.return_value = "Ответ от агента"

        with patch("app.services.yandex_client.chat_service.YandexAgentClient", return_value=mock_client):
            service = ChatService()
            # Агент с .name и .prompt (как ожидает YandexAgentClient)
            agent = MagicMock()
            agent.name = "Копатыч"
            agent.prompt = "Ты медведь."

            result = service.process_message(agent, "session_123", "Привет!")

        assert result == "Ответ от агента"
        mock_client.send_message.assert_called_once_with(
            agent=agent,
            session_id="session_123",
            text="Привет!",
        )


class TestCharacterAgent:
    """CharacterAgent вызывает YandexAgentClient.send_message."""

    def test_character_agent_respond_delegates_to_client(self):
        from app.services.yandex_client.character_agent import CharacterAgent

        mock_client = MagicMock()
        mock_client.send_message.return_value = "Укуси меня пчела!"

        agent = MagicMock()
        agent.name = "Копатыч"
        agent.prompt = "Промпт"
        char_agent = CharacterAgent(agent, mock_client)

        result = char_agent.respond("sess_1", "Как урожай?")

        assert result == "Укуси меня пчела!"
        mock_client.send_message.assert_called_once_with(
            agent=agent, session_id="sess_1", text="Как урожай?"
        )


class TestAgentFactory:
    """AgentFactory создаёт CharacterAgent и кэширует по имени."""

    def test_get_agent_creates_and_caches_character_agent(self):
        from app.services.yandex_client.agent_factory import AgentFactory

        mock_client = MagicMock()
        factory = AgentFactory(mock_client)

        agent1 = MagicMock()
        agent1.name = "Копатыч"
        ca1 = factory.get_agent(agent1)
        ca2 = factory.get_agent(agent1)

        assert ca1 is ca2
        assert agent1.name in factory.agents

    def test_different_agents_get_different_character_agents(self):
        from app.services.yandex_client.agent_factory import AgentFactory

        mock_client = MagicMock()
        factory = AgentFactory(mock_client)

        agent_a = MagicMock()
        agent_a.name = "Копатыч"
        agent_b = MagicMock()
        agent_b.name = "Гермиона"

        ca_a = factory.get_agent(agent_a)
        ca_b = factory.get_agent(agent_b)

        assert ca_a is not ca_b
