"""
Главный pipeline оркестрации.

Правильный порядок:
1. retrieve memory (ChromaDB)
2. planning (опционально)
3. agents discussion (strategy execute)
4. summarize
5. store memory
6. update relationship graph

Без этого pipeline компоненты не связаны — агенты зацикливаются,
память не используется, граф не строится.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("aigod.orchestration.pipeline")

from app.services.agents_orchestration.state import ConversationState


async def run_pipeline(
    user_message: str,
    room_id: int,
    room,
    strategy,
    agents: list,
    chat_service,
    max_rounds: int = 5,
) -> ConversationState:
    """
    Выполнить полный pipeline оркестрации.

    Args:
        user_message: Сообщение пользователя (центр итерации)
        room_id: ID комнаты
        room: Объект Room
        strategy: Стратегия (Circular, Narrator, FullContext)
        agents: Список имён агентов
        chat_service: Функция вызова LLM
        max_rounds: Макс. раундов (защита от бесконечного цикла)

    Returns:
        ConversationState с final_answer и agent_messages
    """
    state = ConversationState(user_message=user_message, room_id=room_id)
    logger.info("pipeline START room_id=%s user_msg_len=%d", room_id, len(user_message))

    # 1. Retrieve memory (ChromaDB / context_memory)
    state.memory_context = await _retrieve_memory(room, user_message)
    if state.memory_context:
        logger.info("pipeline memory retrieved room_id=%s len=%d", room_id, len(state.memory_context))

    # 2. Planning (упрощённый — план = user_message для фокуса)
    state.plan = f"Запрос пользователя: {user_message}"
    logger.debug("pipeline plan set room_id=%s", room_id)

    # 3. Agents discussion через strategy (strategy получает state)
    await _execute_discussion(state, strategy, agents, chat_service, room, max_rounds)

    # 4. Summarize (финальный ответ — последнее значимое сообщение агента)
    if state.agent_messages:
        state.final_answer = state.agent_messages[-1].split(":", 1)[-1].strip()
    logger.info("pipeline discussion done room_id=%s agent_msgs=%d", room_id, len(state.agent_messages))

    # 5. Store memory
    await _store_memory(room, state)
    logger.info("pipeline memory stored room_id=%s", room_id)

    # 6. Update relationship graph
    await _update_relationship_graph(room, state)
    logger.info("pipeline graph updated room_id=%s DONE", room_id)

    return state


async def _retrieve_memory(room, query: str) -> Optional[str]:
    """Загрузить релевантные воспоминания из памяти комнаты."""
    try:
        from app.services.room_services_registry import get_memory_integration

        integration = get_memory_integration(room)
        if not integration:
            return None

        context = await integration.memory_manager.get_relevant_context_async(
            query=query, max_tokens=800
        )
        return context or None
    except Exception as e:
        logger.warning("pipeline _retrieve_memory error: %s", e)
        return None


async def _execute_discussion(
    state: ConversationState,
    strategy,
    agents: list,
    chat_service,
    room,
    max_rounds: int,
) -> None:
    """
    Запустить обсуждение агентов.
    Strategy получает state с user_message, memory_context, plan.
    """
    # Передаём state в strategy через context
    strategy.context.update_memory("_pipeline_state", state)
    strategy.context.update_memory("_user_message", state.user_message)
    strategy.context.update_memory("_memory_context", state.memory_context or "")
    strategy.context.update_memory("_plan", state.plan or "")

    # Запускаем strategy (она использует chat_service с обогащённым промптом)
    round_count = 0
    while round_count < max_rounds:
        messages = await strategy.tick(agents)
        if not messages:
            round_count += 1
            await asyncio.sleep(0.5)
            continue

        for msg in messages:
            if hasattr(msg, "sender") and hasattr(msg, "content"):
                state.append_agent_reply(msg.sender, msg.content)

        round_count += 1
        await asyncio.sleep(0.3)


async def _store_memory(room, state: ConversationState) -> None:
    """Сохранить итог разговора в память."""
    try:
        from app.services.room_services_registry import get_memory_integration
        from app.services.context_memory.models import ImportanceLevel

        integration = get_memory_integration(room)
        if not integration:
            return

        conv_id = f"room_{state.room_id}"
        text = f"User: {state.user_message}\nAnswer: {state.final_answer or '(no answer)'}"
        await integration.memory_manager.add_message(
            content=text,
            sender="system",
            importance=ImportanceLevel.HIGH,
            metadata={"room_id": state.room_id, "pipeline": "orchestration"},
        )
    except Exception as e:
        logger.warning("pipeline _store_memory error: %s", e)


async def _update_relationship_graph(room, state: ConversationState) -> None:
    """Обновить граф отношений после диалога."""
    try:
        from app.services.relationship_model_service import get_relationship_manager

        manager = get_relationship_manager(room)
        agent_names = [a.name for a in room.agents]

        # Обновляем граф по сообщениям агентов
        for msg in state.agent_messages:
            if ": " in msg:
                sender, content = msg.split(": ", 1)
                if sender in agent_names:
                    result = await manager.process_message(
                        message=content,
                        sender=sender,
                        participants=agent_names,
                    )
                    if result:
                        logger.debug("pipeline graph updated from msg sender=%s", sender)
    except Exception as e:
        logger.warning("pipeline _update_relationship_graph error: %s", e)
