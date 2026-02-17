"""
Сервис для генерации ответов агентов через YandexGPT.
Связывает DB-модель Agent (personality) с YandexAgentClient (prompt).
"""

from typing import Optional

from app.config import config


class AgentPromptAdapter:
    """Адаптер: Agent (SQLAlchemy) -> объект с .name и .prompt для YandexAgentClient."""

    def __init__(self, agent):
        self.name = agent.name
        self.prompt = agent.personality or ""


def get_agent_response(agent, session_id: str, text: str) -> str:
    """
    Получить ответ агента от LLM (режим single — один агент).

    Args:
        agent: SQLAlchemy Agent (personality = промпт персонажа)
        session_id: ID сессии для истории диалога
        text: текст сообщения пользователя

    Returns:
        Текст ответа агента или fallback при ошибке.
    """
    if not config.YANDEX_CLOUD_FOLDER or not config.YANDEX_CLOUD_API_KEY:
        return "Агент временно недоступен. Настройте YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY в .env."

    try:
        from app.services.yandex_client.chat_service import ChatService

        adapter = AgentPromptAdapter(agent)
        chat_service = ChatService()
        return chat_service.process_message(adapter, session_id, text)
    except Exception as e:
        print(f"LLM error: {e}")
        return "Ой-ой, связь пропала! Попробуй позже."
