"""
YandexAgentAdapter — адаптер для использования YandexAgentClient в оркестрации.

Как в examples/usage.py: стратегии вызывают chat_service(agent_name, session_id, prompt, context).
Адаптер усиливает промпт контекстом разговора и передаёт в YandexAgentClient.
"""
import asyncio
from datetime import datetime
from typing import Optional

from app.services.agents_orchestration.context import ConversationContext
from app.services.prompts import get_system_prompt
from app.services.yandex_client.yandex_agent_client import YandexAgentClient, Agent


class YandexAgentAdapter:
    """
    Адаптер для использования YandexAgentClient в оркестрации.
    Регистрирует агентов по имени и промпту; при вызове добавляет контекст из ConversationContext.
    """

    def __init__(self, client: YandexAgentClient):
        self.client = client
        self.agents: dict[str, Agent] = {}
        self.session_counter = 0

    def register_agent(self, name: str, prompt: str) -> None:
        """Регистрация агента. Промпт дополняется системными инструкциями."""
        system = get_system_prompt(mode="orchestration")
        full_prompt = f"{system}\n\n---\n\n{prompt}"
        self.agents[name] = Agent(name, full_prompt)

    def register_agents_from_room(self, room_agents: list) -> None:
        """
        Регистрация агентов из комнаты (DB Agent с name, personality).
        """
        for agent in room_agents:
            self.register_agent(agent.name, agent.personality or "")

    def _create_session_id(self, strategy_name: str) -> str:
        """Создание уникального ID сессии."""
        self.session_counter += 1
        return f"{strategy_name}_session_{self.session_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def __call__(
        self,
        agent_name: str,
        session_id: str,
        prompt: str,
        context: Optional[ConversationContext] = None,
    ) -> str:
        """
        Отправка сообщения агенту через YandexAgentClient.

        Усиливает промпт контекстом разговора (последние сообщения), как в usage.py.
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return f"[{agent_name}] Агент не найден"

        if context and context.history:
            recent = context.get_recent_messages(5)
            context_text = "\n".join([f"{m.sender}: {m.content}" for m in recent])
            enhanced_prompt = f"""
Контекст разговора (последние сообщения):
{context_text}

Текущая задача/запрос:
{prompt}

Продолжи разговор естественно, учитывая контекст и свою роль.
"""
        else:
            enhanced_prompt = prompt

        actual_session_id = session_id or self._create_session_id("unknown")
        response = self.client.send_message(agent, actual_session_id, enhanced_prompt)

        await asyncio.sleep(0.5)
        return response
