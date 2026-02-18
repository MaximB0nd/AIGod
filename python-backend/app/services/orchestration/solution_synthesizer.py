"""
Solution Synthesizer — FINAL DECISION MAKER.

НЕ summarizer. Summarizer: "кратко перескажи диалог".
Synthesizer: "прими решение и ответь пользователю".

Этап ВСЕГДА выполняется после discussion. Обязательный.
"""
import logging
from typing import Callable, Awaitable, Any

logger = logging.getLogger("aigod.orchestration.synthesizer")


class SolutionSynthesizer:
    """
    Принимает решение о завершении задачи и формирует финальный ответ пользователю.
    """

    def __init__(self, chat_service: Callable[..., Awaitable[str]], agent_name: str = "synthesizer"):
        self.chat_service = chat_service
        self.agent_name = agent_name

    async def synthesize(self, state: Any) -> str:
        """
        Принять решение и сформировать финальный ответ.

        Args:
            state: TaskState с user_message, plan, discussion_messages

        Returns:
            Финальный ответ пользователю.
        """
        agent_messages = _format_discussion(state)
        if not agent_messages.strip():
            return state.user_message or ""

        prompt = f"""
You are the FINAL DECISION MAKER.

USER REQUEST:
{state.user_message}

PLAN:
{state.plan or "(no plan)"}

AGENT DISCUSSION:
{agent_messages}

Your task:
1. Decide if the task is solved
2. Produce final answer to the user
3. Stop the discussion

This is the FINAL message.
"""
        try:
            result = await self.chat_service(
                self.agent_name,
                "synthesizer_session",
                prompt,
                context=None,
            )
            return result.strip() if result else agent_messages
        except Exception as e:
            logger.warning("SolutionSynthesizer.synthesize failed: %s", e)
            return agent_messages


def _format_discussion(state: Any) -> str:
    """Форматировать discussion_messages в текст agent_messages."""
    lines = []
    for m in getattr(state, "discussion_messages", []):
        if hasattr(m, "sender") and hasattr(m, "content"):
            lines.append(f"{m.sender}: {m.content}")
    return "\n".join(lines) if lines else ""
