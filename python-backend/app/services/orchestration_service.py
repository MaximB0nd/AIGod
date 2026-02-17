"""
Сервис оркестрации для комнат.

Создаёт OrchestrationClient + YandexAgentAdapter из room.agents,
как в examples/usage.py.
"""
from typing import Optional

from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.strategies import (
    CircularStrategy,
    FullContextStrategy,
    NarratorStrategy,
)
from app.services.agents_orchestration.yandex_adapter import YandexAgentAdapter
from app.services.yandex_client.yandex_agent_client import YandexAgentClient


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

    adapter = YandexAgentAdapter(yandex_client)
    adapter.register_agents_from_room(room.agents)

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
