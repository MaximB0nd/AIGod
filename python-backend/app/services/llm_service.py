"""
Сервис для генерации ответов агентов через YandexGPT.
Связывает DB-модель Agent (personality) с YandexAgentClient (prompt).
Обогащает промпт контекстом отношений, памяти и эмоций (если доступны).
"""

import logging
from typing import Optional

from app.config import config

logger = logging.getLogger("aigod.llm")


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
        logger.warning("LLM: Yandex ключи не настроены (YANDEX_CLOUD_FOLDER=%s YANDEX_CLOUD_API_KEY=%s)", bool(config.YANDEX_CLOUD_FOLDER), bool(config.YANDEX_CLOUD_API_KEY))
        return "Агент временно недоступен. Настройте YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY в .env."

    try:
        logger.info("LLM: запрос agent=%s session=%s text_len=%d room_id=%s", agent.name, session_id, len(text), getattr(room, "id", None) if room else None)
        from app.services.yandex_client.chat_service import ChatService
        from app.services.prompt_enhancer import enhance_prompt_with_relationship
        from app.services.prompts import get_system_prompt
        from app.services.relationship_model_service import get_relationship_manager

        adapter = AgentPromptAdapter(agent)
        system = get_system_prompt(mode="single")
        base_prompt = f"{system}\n\n---\n\n{adapter.prompt}"

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
        result = chat_service.process_message(adapter, session_id, text)
        logger.info("LLM: ответ получен agent=%s len=%d preview=%.50s...", agent.name, len(result) if result else 0, (result or "")[:50])
        return result
    except Exception as e:
        logger.exception("LLM error: %s", e)
        return "Ой-ой, связь пропала! Попробуй позже."
