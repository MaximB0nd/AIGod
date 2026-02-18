"""
Единый orchestration pipeline executor.

Каждый запрос ОБЯЗАТЕЛЬНО проходит фиксированные стадии:
NEW_TASK → RETRIEVE_MEMORY → PLAN → DISCUSS → SYNTHESIZE → STORE_MEMORY → FACT_EXTRACTION → UPDATE_GRAPH → DONE

SolutionSynthesizer — FINAL DECISION MAKER, ВСЕГДА после discussion.
"""
import asyncio
import logging
from typing import Callable, Awaitable, Optional, Any

from .stages import PipelineStage, TaskState
from .solution_synthesizer import SolutionSynthesizer
from .fact_extractor import FactExtractor

logger = logging.getLogger("aigod.orchestration.executor")


class PipelineExecutor:
    """
    Движок выполнения: каждый этап — обязательный шаг.
    """
    def __init__(
        self,
        room: Any,
        chat_service: Callable[..., Awaitable[str]],
        strategy: Any,
        agents: list[str],
        on_message: Optional[Callable[[Any], Awaitable[None]]] = None,
        max_discuss_rounds: int = 5,
    ):
        self.room = room
        self.chat_service = chat_service
        self.strategy = strategy
        self.agents = agents
        self.on_message = on_message
        self.max_discuss_rounds = max_discuss_rounds

    async def run(self, user_message: str, sender: str = "user") -> TaskState:
        """
        Выполнить полный pipeline. Каждый этап — обязательный.
        """
        state = TaskState(
            user_message=user_message,
            room_id=self.room.id,
            agent_names=self.agents.copy(),
            room=self.room,
            sender=sender,
        )
        logger.info("pipeline_executor RUN room_id=%s user_len=%d", state.room_id, len(user_message))

        try:
            # 1. RETRIEVE_MEMORY — обязательно
            state.transition_to(PipelineStage.RETRIEVE_MEMORY)
            await self._stage_retrieve_memory(state)
            logger.info("pipeline_executor stage=RETRIEVE_MEMORY done room_id=%s", state.room_id)

            # 2. PLAN — обязательно
            state.transition_to(PipelineStage.PLAN)
            await self._stage_plan(state)
            logger.info("pipeline_executor stage=PLAN done room_id=%s", state.room_id)

            # 3. DISCUSS — обязательно (стратегия)
            state.transition_to(PipelineStage.DISCUSS)
            await self._stage_discuss(state)
            logger.info("pipeline_executor stage=DISCUSS done room_id=%s msgs=%d", state.room_id, len(state.discussion_messages))

            # 4. SYNTHESIZE — обязательно (SolutionSynthesizer: FINAL DECISION MAKER)
            state.transition_to(PipelineStage.SYNTHESIZE)
            await self._stage_synthesize(state)
            logger.info("pipeline_executor stage=SYNTHESIZE done room_id=%s", state.room_id)

            # 5. STORE_MEMORY — обязательно
            state.transition_to(PipelineStage.STORE_MEMORY)
            await self._stage_store_memory(state)
            logger.info("pipeline_executor stage=STORE_MEMORY done room_id=%s", state.room_id)

            # 6. FACT_EXTRACTION — обязательно (триплеты для графа)
            state.transition_to(PipelineStage.FACT_EXTRACTION)
            await self._stage_extract_facts(state)
            logger.info("pipeline_executor stage=FACT_EXTRACTION done room_id=%s facts=%d", state.room_id, len(state.extracted_facts))

            # 7. UPDATE_GRAPH — обязательно (включая facts)
            state.transition_to(PipelineStage.UPDATE_GRAPH)
            await self._stage_update_graph(state)
            logger.info("pipeline_executor stage=UPDATE_GRAPH done room_id=%s", state.room_id)

        except Exception as e:
            logger.exception("pipeline_executor ERROR room_id=%s stage=%s: %s", state.room_id, state.stage, e)
            state.error = str(e)

        state.transition_to(PipelineStage.DONE)
        logger.info("pipeline_executor DONE room_id=%s", state.room_id)
        return state

    async def _stage_retrieve_memory(self, state: TaskState) -> None:
        """Обязательный этап: загрузить память."""
        try:
            from app.services.room_services_registry import get_memory_integration
            integration = get_memory_integration(self.room)
            if integration:
                state.memory_context = await integration.memory_manager.get_relevant_context_async(
                    query=state.user_message, max_tokens=800
                )
            if not state.memory_context:
                state.memory_context = ""
        except Exception as e:
            logger.warning("_stage_retrieve_memory: %s", e)
            state.memory_context = ""

    async def _stage_plan(self, state: TaskState) -> None:
        """Обязательный этап: план (простой или через LLM)."""
        # Простой план: фокус на запросе пользователя
        state.plan = f"Запрос пользователя: {state.user_message}"
        # Опционально: LLM-планировщик при необходимости

    async def _stage_discuss(self, state: TaskState) -> None:
        """Обязательный этап: обсуждение агентов через стратегию."""
        # Настраиваем context для стратегии
        self.strategy.context.current_user_message = state.user_message
        self.strategy.context.update_memory("_user_message", state.user_message)
        self.strategy.context.update_memory("_memory_context", state.memory_context or "")
        self.strategy.context.update_memory("_plan", state.plan or "")

        # Обработка пользовательского сообщения (для circular и др.)
        initial_messages = await self.strategy.handle_user_message(state.user_message)
        for msg in initial_messages:
            state.discussion_messages.append(msg)
            self.strategy.context.add_message(msg)
            if self.on_message and hasattr(msg, "type"):
                from app.services.agents_orchestration.message_type import MessageType
                if msg.type in (MessageType.AGENT, MessageType.NARRATOR, MessageType.SUMMARIZED):
                    await self.on_message(msg)

        round_count = 0
        while round_count < self.max_discuss_rounds:
            if self.strategy.should_stop():
                break

            messages = await self.strategy.tick(self.agents)
            if not messages:
                round_count += 1
                await asyncio.sleep(0.3)
                continue

            for msg in messages:
                state.discussion_messages.append(msg)
                if hasattr(msg, "sender") and hasattr(msg, "content"):
                    self.strategy.context.add_message(msg)
                    if self.on_message:
                        await self.on_message(msg)

            round_count += 1
            await asyncio.sleep(0.3)

    async def _stage_synthesize(self, state: TaskState) -> None:
        """Обязательный этап: SolutionSynthesizer — FINAL DECISION MAKER. ВСЕГДА выполняется."""
        synth_agent = self.agents[-1] if self.agents else "System"
        synthesizer = SolutionSynthesizer(chat_service=self.chat_service, agent_name=synth_agent)
        state.synthesized_answer = await synthesizer.synthesize(state)

        if state.synthesized_answer and self.on_message:
            from app.services.agents_orchestration.message import Message
            from app.services.agents_orchestration.message_type import MessageType
            from datetime import datetime
            synth_msg = Message(
                content=state.synthesized_answer,
                type=MessageType.SUMMARIZED,
                sender="Система",
                timestamp=datetime.now(),
                metadata={"pipeline": "synthesize", "authority": "final_decision"},
            )
            await self.on_message(synth_msg)

    async def _stage_store_memory(self, state: TaskState) -> None:
        """Обязательный этап: сохранить в память."""
        try:
            from app.services.room_services_registry import get_memory_integration
            from app.services.context_memory.models import ImportanceLevel

            integration = get_memory_integration(self.room)
            if integration:
                text = f"User: {state.user_message}\nAnswer: {state.synthesized_answer or '(no answer)'}"
                await integration.memory_manager.add_message(
                    content=text,
                    sender="system",
                    importance=ImportanceLevel.HIGH,
                    metadata={"room_id": state.room_id, "pipeline": "executor"},
                )
                state.memory_stored = True
        except Exception as e:
            logger.warning("_stage_store_memory: %s", e)

    async def _stage_extract_facts(self, state: TaskState) -> None:
        """Обязательный этап: извлечь структурированные факты (триплеты) для графа."""
        extractor = FactExtractor(chat_service=self.chat_service)
        state.extracted_facts = await extractor.extract(state)

    async def _stage_update_graph(self, state: TaskState) -> None:
        """Обязательный этап: обновить граф (из facts + heuristic по сообщениям)."""
        try:
            from app.services.relationship_model_service import get_relationship_manager

            manager = get_relationship_manager(self.room)
            if state.extracted_facts:
                manager.update_from_facts(state.extracted_facts, state.agent_names)
            for msg in state.discussion_messages:
                if hasattr(msg, "sender") and hasattr(msg, "content"):
                    await manager.process_message(
                        message=msg.content,
                        sender=msg.sender,
                        participants=state.agent_names,
                    )
            state.graph_updated = True
        except Exception as e:
            logger.warning("_stage_update_graph: %s", e)
