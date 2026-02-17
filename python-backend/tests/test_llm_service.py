"""
Тесты для app.services.llm_service.
Проверяют: AgentPromptAdapter, fallback при отсутствии ключей, вызов ChatService.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.services.llm_service import AgentPromptAdapter, get_agent_response


class FakeAgent:
    """Подмена Agent (SQLAlchemy) с personality и name."""
    def __init__(self, name: str, personality: str):
        self.name = name
        self.personality = personality


class TestAgentPromptAdapter:
    """Проверка адаптера Agent -> объект с .name и .prompt для YandexAgentClient."""

    def test_maps_personality_to_prompt(self):
        agent = FakeAgent(name="Копатыч", personality="Ты добрый медведь.")
        adapter = AgentPromptAdapter(agent)
        assert adapter.name == "Копатыч"
        assert adapter.prompt == "Ты добрый медведь."

    def test_empty_personality_becomes_empty_string(self):
        agent = FakeAgent(name="Пустой", personality="")
        adapter = AgentPromptAdapter(agent)
        assert adapter.prompt == ""

    def test_none_personality_becomes_empty_string(self):
        agent = MagicMock()
        agent.name = "Test"
        agent.personality = None
        adapter = AgentPromptAdapter(agent)
        assert adapter.prompt == ""


class TestGetAgentResponse:
    """Проверка get_agent_response: fallback, мок ChatService."""

    @patch("app.services.llm_service.config")
    def test_returns_fallback_when_no_api_keys(self, mock_config):
        mock_config.YANDEX_CLOUD_FOLDER = ""
        mock_config.YANDEX_CLOUD_API_KEY = ""
        agent = FakeAgent("Копатыч", "Персонаж")
        result = get_agent_response(agent, "session_1", "Привет!")
        assert "YANDEX_CLOUD" in result
        assert "Настройте" in result or "недоступен" in result.lower()

    @patch("app.services.llm_service.config")
    def test_returns_fallback_when_folder_empty(self, mock_config):
        mock_config.YANDEX_CLOUD_FOLDER = ""
        mock_config.YANDEX_CLOUD_API_KEY = "some-key"
        agent = FakeAgent("Копатыч", "Персонаж")
        result = get_agent_response(agent, "session_1", "Привет!")
        assert "YANDEX_CLOUD" in result or "недоступен" in result.lower()

    @patch("app.services.yandex_client.chat_service.ChatService")
    @patch("app.services.llm_service.config")
    def test_calls_chat_service_when_keys_set(self, mock_config, mock_chat_cls):
        mock_config.YANDEX_CLOUD_FOLDER = "folder"
        mock_config.YANDEX_CLOUD_API_KEY = "key"
        mock_chat = MagicMock()
        mock_chat.process_message.return_value = "Укуси меня пчела! Привет, дружище!"
        mock_chat_cls.return_value = mock_chat

        agent = FakeAgent("Копатыч", "Ты медведь-огородник.")
        result = get_agent_response(agent, "room_1_agent_5", "Как дела?")

        assert result == "Укуси меня пчела! Привет, дружище!"
        mock_chat.process_message.assert_called_once()
        call_args = mock_chat.process_message.call_args
        # Первый аргумент — адаптер (agent), второй — session_id, третий — text
        adapter = call_args[0][0]
        assert adapter.name == "Копатыч"
        assert adapter.prompt == "Ты медведь-огородник."
        assert call_args[0][1] == "room_1_agent_5"
        assert call_args[0][2] == "Как дела?"

    @patch("app.services.yandex_client.chat_service.ChatService")
    @patch("app.services.llm_service.config")
    def test_returns_error_message_on_exception(self, mock_config, mock_chat_cls):
        mock_config.YANDEX_CLOUD_FOLDER = "folder"
        mock_config.YANDEX_CLOUD_API_KEY = "key"
        mock_chat_cls.side_effect = RuntimeError("API недоступен")

        agent = FakeAgent("Копатыч", "Персонаж")
        result = get_agent_response(agent, "session_1", "Привет")

        assert "связь пропала" in result or "позже" in result
