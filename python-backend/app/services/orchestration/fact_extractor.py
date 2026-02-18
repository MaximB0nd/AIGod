"""
Fact Extractor — извлечение структурированных фактов (триплетов) из диалога.

Перед обновлением графа: facts = fact_extractor.extract(state); graph.update(facts).

Триплеты: (Subject) -> predicate -> (Object)
Пример: (User) -> wants -> build startup
        (Agent A) -> suggested -> market research
"""
import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("aigod.orchestration.fact_extractor")


@dataclass
class Fact:
    """Структурированный факт-триплет."""
    subject: str
    predicate: str
    obj: str  # object — зарезервировано
    source: str = ""  # sender сообщения


class FactExtractor:
    """
    Извлекает факты из диалога для обновления графа.
    """
    def __init__(self, chat_service=None):
        self.chat_service = chat_service

    async def extract(self, state: Any) -> List[Fact]:
        """
        Извлечь структурированные факты из обсуждения.

        Args:
            state: TaskState с discussion_messages, user_message

        Returns:
            Список Fact (subject, predicate, object)
        """
        discussion_text = self._format_discussion(state)
        if not discussion_text.strip():
            return []

        if self.chat_service and hasattr(state, "agent_names") and state.agent_names:
            try:
                return await self._extract_via_llm(state, discussion_text)
            except Exception as e:
                logger.warning("FactExtractor LLM extract failed: %s", e)

        return self._extract_heuristic(discussion_text)

    def _format_discussion(self, state: Any) -> str:
        lines = []
        for m in getattr(state, "discussion_messages", []):
            if hasattr(m, "sender") and hasattr(m, "content"):
                lines.append(f"{m.sender}: {m.content}")
        return "\n".join(lines)

    async def _extract_via_llm(self, state: Any, discussion_text: str) -> List[Fact]:
        """Извлечь факты через LLM."""
        agent_name = state.agent_names[0] if state.agent_names else "System"
        prompt = f"""
Extract structured facts from this discussion as SUBJECT -> PREDICATE -> OBJECT triplets.

USER REQUEST: {state.user_message}

DISCUSSION:
{discussion_text}

Output ONLY triplets, one per line:
Subject | predicate | Object

Examples:
User | wants | build startup
AgentName | suggested | market research
AgentName | agreed_with | OtherAgent

Output (one triplet per line):
"""
        response = await self.chat_service(
            agent_name,
            "fact_extraction_session",
            prompt,
            context=None,
        )
        return self._parse_triplets(response)

    def _parse_triplets(self, text: str) -> List[Fact]:
        """Распарсить текст в список Fact."""
        facts = []
        for line in (text or "").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = re.split(r"\s*\|\s*", line, 2)
            if len(parts) >= 3:
                facts.append(Fact(
                    subject=parts[0].strip(),
                    predicate=parts[1].strip(),
                    obj=parts[2].strip(),
                ))
        return facts

    def _extract_heuristic(self, text: str) -> List[Fact]:
        """Эвристическое извлечение (fallback)."""
        facts = []
        for line in text.split("\n"):
            m = re.search(r"(\w+)\s*:\s*(.+)", line)
            if m:
                subject = m.group(1)
                content = m.group(2).strip()
                if len(content) > 3:
                    facts.append(Fact(
                        subject=subject,
                        predicate="said",
                        obj=content[:200],
                    ))
        return facts
