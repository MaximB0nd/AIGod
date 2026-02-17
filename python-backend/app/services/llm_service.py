"""
Сервис для генерации ответов агентов через YandexGPT.
Связывает DB-модель Agent (personality) с YandexAgentClient (prompt).
Обогащает промпт контекстом отношений, памяти и эмоций (если доступны).
"""

from typing import Optional

from app.config import config


class AgentPromptAdapter:
    """Адаптер: Agent (SQLAlchemy) -> объект с .name и .prompt для YandexAgentClient."""

    def __init__(self, agent):
        self.name = agent.name
        self.prompt = agent.personality or ""


def get_agent_response(
    agent,
    session_id: str,
    text: str,
    *,
    room=None,
) -> str:
    """
    Получить ответ агента от LLM (режим single — один агент).

    Args:
        agent: SQLAlchemy Agent (personality = промпт персонажа)
        session_id: ID сессии для истории диалога
        text: текст сообщения пользователя
        room: опционально — комната для обогащения промпта (отношения, память, эмоции)

    Returns:
        Текст ответа агента или fallback при ошибке.
    """
    if not config.YANDEX_CLOUD_FOLDER or not config.YANDEX_CLOUD_API_KEY:
        return "Агент временно недоступен. Настройте YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY в .env."

    try:
        from app.services.yandex_client.chat_service import ChatService
        from app.services.prompt_enhancer import enhance_prompt_with_relationship
        from app.services.relationship_model_service import get_relationship_manager

        adapter = AgentPromptAdapter(agent)
        base_prompt = adapter.prompt

        # Обогащаем характер агента контекстом отношений
        if room and room.agents:
            try:
                rel_manager = get_relationship_manager(room)
                base_prompt = enhance_prompt_with_relationship(
                    rel_manager, agent.name, base_prompt
                )
            except Exception:
                pass

        adapter.prompt = base_prompt
        chat_service = ChatService()
        return chat_service.process_message(adapter, session_id, text)
    except Exception as e:
        print(f"LLM error: {e}")
        return "Ой-ой, связь пропала! Попробуй позже."
