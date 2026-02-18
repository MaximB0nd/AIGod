"""
Сервис оркестрации для комнат.

Создаёт OrchestrationClient + YandexAgentAdapter из room.agents,
как в examples/usage.py. Обогащает промпты контекстом отношений.
"""
import logging
from typing import Optional

logger = logging.getLogger("aigod.orchestration.service")

from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.strategies import (
    CircularStrategy,
    FullContextStrategy,
    NarratorStrategy,
)
from app.constants import (
    NARRATOR_AGENT_NAME,
    NARRATOR_PERSONALITY,
    SUMMARIZER_AGENT_NAME,
    SUMMARIZER_PERSONALITY,
)
from app.services.agents_orchestration.yandex_adapter import YandexAgentAdapter
from app.services.prompt_enhancer import enhance_prompt_with_relationship, enhance_prompt_with_emotional_state
from app.services.relationship_model_service import get_relationship_manager
from app.services.room_services_registry import get_emotional_integration
from app.services.yandex_client.yandex_agent_client import YandexAgentClient


class _RelationshipEnhancingAdapter:
    """Оборачивает YandexAgentAdapter: контекст отношений + память (ChromaDB)."""

    def __init__(self, inner: YandexAgentAdapter, room):
        self.inner = inner
        self.room = room
        self._rel_manager = None
        self._memory_integration = None

    def _get_rel_manager(self):
        if self._rel_manager is None:
            try:
                self._rel_manager = get_relationship_manager(self.room)
            except Exception:
                pass
        return self._rel_manager

    def _get_memory_integration(self):
        if self._memory_integration is None:
            try:
                from app.services.room_services_registry import get_memory_integration
                self._memory_integration = get_memory_integration(self.room)
            except Exception:
                pass
        return self._memory_integration

    async def __call__(self, agent_name: str, session_id: str, prompt: str, context=None) -> str:
        # 1. Память: обогатить промпт контекстом из ChromaDB
        user_msg = None
        if context:
            user_msg = getattr(context, "current_user_message", None) or context.get_memory("_user_message")
        mem_integration = self._get_memory_integration()
        if mem_integration and (user_msg or prompt):
            try:
                prompt = await mem_integration.enhance_prompt_with_context_async(
                    agent_name, prompt, query=user_msg or prompt
                )
                if context and user_msg:
                    ctx = await mem_integration.memory_manager.get_relevant_context_async(
                        user_msg or prompt, max_tokens=500
                    )
                    if ctx:
                        context.update_memory("_memory_context", ctx)
            except Exception as e:
                logger.debug("memory enhance failed: %s", e)
        # 2. Отношения
        rel_manager = self._get_rel_manager()
        if rel_manager:
            prompt = enhance_prompt_with_relationship(rel_manager, agent_name, prompt)
        # 3. Эмоции
        emo = get_emotional_integration(self.room) if hasattr(self, "room") else None
        if emo:
            prompt = enhance_prompt_with_emotional_state(emo, agent_name, prompt)
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
        logger.warning("create_orchestration_client room_id=%s agents=[]", room.id)
        return None

    try:
        yandex_client = YandexAgentClient()
        logger.info("create_orchestration_client room_id=%s YandexAgentClient OK", room.id)
    except Exception as e:
        logger.warning("create_orchestration_client room_id=%s YandexAgentClient fail: %s", room.id, e)
        return None

    base_adapter = YandexAgentAdapter(yandex_client)
    base_adapter.register_agents_from_room(room.agents)
    # circular: ghost Суммаризатор для синтеза. narrator: Рассказчик — реальный агент в room.agents.
    if orchestration_type == "circular":
        base_adapter.register_agent(SUMMARIZER_AGENT_NAME, SUMMARIZER_PERSONALITY)
        all_agent_names = agent_names + [SUMMARIZER_AGENT_NAME]
    else:
        all_agent_names = agent_names
    adapter = _RelationshipEnhancingAdapter(base_adapter, room)
    client = OrchestrationClient(all_agent_names, adapter, room_id=room.id)

    if orchestration_type == "circular":
        # Circular без Рассказчика — только агенты по кругу + Суммаризатор (ghost)
        strategy = CircularStrategy(
            client.context,
            max_rounds=50,
        )
    elif orchestration_type == "narrator":
        narrator = agent_names[0]
        strategy = NarratorStrategy(
            client.context,
            narrator_agent=narrator,
            story_topic=room.description or "История",
            narrator_interval=2,
        )
    elif orchestration_type == "full_context":
        base_adapter.register_agent(SUMMARIZER_AGENT_NAME, SUMMARIZER_PERSONALITY)
        strategy = FullContextStrategy(
            client.context,
            initial_prompt=room.description or "Обсуждение",
            summary_agent=SUMMARIZER_AGENT_NAME,
        )
    else:
        return None

    client.set_strategy(strategy)
    logger.info("create_orchestration_client room_id=%s type=%s strategy=%s agents=%s", room.id, orchestration_type, strategy.__class__.__name__, agent_names)
    return client


def create_pipeline_components(room):
    """
    Создать компоненты для PipelineExecutor: chat_service, strategy, context.

    Используется как единая точка входа для pipeline — без long-running client.
    """
    orchestration_type = getattr(room, "orchestration_type", None) or "single"
    if orchestration_type == "single":
        return None

    agent_names = [a.name for a in room.agents]
    if not agent_names:
        return None

    try:
        yandex_client = YandexAgentClient()
    except Exception as e:
        logger.warning("create_pipeline_components YandexAgentClient fail: %s", e)
        return None

    base_adapter = YandexAgentAdapter(yandex_client)
    base_adapter.register_agents_from_room(room.agents)
    if orchestration_type == "circular":
        base_adapter.register_agent(SUMMARIZER_AGENT_NAME, SUMMARIZER_PERSONALITY)
    elif orchestration_type == "full_context":
        base_adapter.register_agent(SUMMARIZER_AGENT_NAME, SUMMARIZER_PERSONALITY)
    adapter = _RelationshipEnhancingAdapter(base_adapter, room)

    from app.services.agents_orchestration.context import ConversationContext

    all_agent_names = (agent_names + [SUMMARIZER_AGENT_NAME]) if orchestration_type == "circular" else agent_names
    context = ConversationContext(participants=all_agent_names.copy())
    agents_for_strategy = all_agent_names if orchestration_type == "circular" else agent_names

    if orchestration_type == "circular":
        strategy = CircularStrategy(
            context,
            max_rounds=50,
        )
    elif orchestration_type == "narrator":
        strategy = NarratorStrategy(
            context,
            narrator_agent=agent_names[0],
            story_topic=room.description or "История",
            narrator_interval=2,
        )
    elif orchestration_type == "full_context":
        strategy = FullContextStrategy(
            context,
            initial_prompt=room.description or "Обсуждение",
            summary_agent=SUMMARIZER_AGENT_NAME,
            max_iterations=5,
            agents_per_iteration=2,
        )
    else:
        return None

    strategy.context = context
    strategy.chat_service = adapter
    return {
        "chat_service": adapter,
        "strategy": strategy,
        "context": context,
        "agents": agents_for_strategy,
    }
