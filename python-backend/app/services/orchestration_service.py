"""
Сервис оркестрации для комнат.

Создаёт OrchestrationClient + YandexAgentAdapter из room.agents,
как в examples/usage.py. Обогащает промпты контекстом отношений.
"""
from typing import Optional

from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.strategies import (
    CircularStrategy,
    FullContextStrategy,
    NarratorStrategy,
)
from app.services.agents_orchestration.yandex_adapter import YandexAgentAdapter
from app.services.prompt_enhancer import enhance_prompt_with_relationship
from app.services.relationship_model_service import get_relationship_manager
from app.services.yandex_client.yandex_agent_client import YandexAgentClient


class _RelationshipEnhancingAdapter:
    """Оборачивает YandexAgentAdapter, добавляя контекст отношений в промпт."""

    def __init__(self, inner: YandexAgentAdapter, room):
        self.inner = inner
        self.room = room
        self._rel_manager = None

    def _get_rel_manager(self):
        if self._rel_manager is None:
            try:
                self._rel_manager = get_relationship_manager(self.room)
            except Exception:
                pass
        return self._rel_manager

    async def __call__(self, agent_name: str, session_id: str, prompt: str, context=None) -> str:
        rel_manager = self._get_rel_manager()
        if rel_manager:
            prompt = enhance_prompt_with_relationship(rel_manager, agent_name, prompt)
        return await self.inner(agent_name, session_id, prompt, context)


def create_orchestration_client(room) -> Optional[OrchestrationClient]:
    """
    Создать OrchestrationClient для комнаты.

    Как в usage.py: YandexAgentClient → YandexAgentAdapter → OrchestrationClient.
    Стратегия выбирается по room.orchestration_type.
    """
    orchestration_type = getattr(room, "orchestration_type", None) or "single"
    if orchestration_type == "single":
        return None

    agent_names = [a.name for a in room.agents]
    if not agent_names:
        return None

    try:
        yandex_client = YandexAgentClient()
    except Exception:
        return None

    base_adapter = YandexAgentAdapter(yandex_client)
    base_adapter.register_agents_from_room(room.agents)
    adapter = _RelationshipEnhancingAdapter(base_adapter, room)

    client = OrchestrationClient(agent_names, adapter)

    if orchestration_type == "circular":
        strategy = CircularStrategy(client.context)
    elif orchestration_type == "narrator":
        narrator = agent_names[0]
        strategy = NarratorStrategy(
            client.context,
            narrator_agent=narrator,
            story_topic=room.description or "История",
            narrator_interval=2,
        )
    elif orchestration_type == "full_context":
        strategy = FullContextStrategy(
            client.context,
            initial_prompt=room.description or "Обсуждение",
            summary_agent=agent_names[-1] if agent_names else None,
            max_rounds=2,
            agents_per_round=2,
        )
    else:
        return None

    client.set_strategy(strategy)
    return client
