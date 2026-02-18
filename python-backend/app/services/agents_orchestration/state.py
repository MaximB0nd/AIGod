"""
Состояние разговора — центр orchestration pipeline.

User message — ядро итерации. Агенты получают полный контекст:
user_message, plan, memory_context, agent_messages.
Без этого агенты зацикливаются и игнорируют пользователя.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConversationState:
    """Состояние диалога, передаётся через весь pipeline оркестрации."""
    user_message: str
    plan: Optional[str] = None
    memory_context: Optional[str] = None
    agent_messages: List[str] = field(default_factory=list)
    final_answer: Optional[str] = None
    room_id: Optional[int] = None

    def append_agent_reply(self, agent_name: str, content: str) -> None:
        """Добавить ответ агента в историю обсуждения."""
        self.agent_messages.append(f"{agent_name}: {content}")

    def get_discussion_text(self) -> str:
        """Текст обсуждения для промпта агента."""
        return "\n".join(self.agent_messages) if self.agent_messages else "(пока нет обсуждения)"
