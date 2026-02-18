"""
Эвристический анализатор отношений без LLM.

Обновляет граф по ключевым словам (согласен, не согласен, поддерживаю и т.д.)
когда LLM-анализатор недоступен.
"""
import re
import logging
from typing import Dict, List

from .models import AnalysisResult
from datetime import datetime

logger = logging.getLogger("aigod.relationship.heuristic")


# Ключевые слова: фраза -> (направление, сила)
# Направление: +1 улучшает, -1 ухудшает
POSITIVE_PATTERNS = [
    (r"\bсогласен\b", 0.15),
    (r"\bподдерживаю\b", 0.15),
    (r"\bотлично\b", 0.1),
    (r"\bправильно\b", 0.1),
    (r"\bхорошо\b", 0.08),
    (r"\bда\s*,?\s*(именно|верно)", 0.12),
    (r"\bполностью\s+согласен\b", 0.2),
    (r"\bточно\b", 0.08),
]
NEGATIVE_PATTERNS = [
    (r"\bне\s+согласен\b", -0.15),
    (r"\bспорно\b", -0.1),
    (r"\bнеправильно\b", -0.12),
    (r"\bнесогласен\b", -0.15),
    (r"\bневерно\b", -0.12),
]


class HeuristicRelationshipAnalyzer:
    """Анализатор без LLM: правило-based оценка влияния на отношения."""

    def __init__(self, influence_coefficient: float = 0.5):
        self.influence_coefficient = influence_coefficient
        self._callbacks: list = []

    def on_analysis(self, callback) -> None:
        """Подписка (для совместимости с RelationshipManager). Не используется."""
        self._callbacks.append(callback)

    async def analyze_message(
        self,
        message: str,
        sender: str,
        participants: List[str],
        context: List[str] | None = None,
        message_id: str | None = None,
    ) -> AnalysisResult | None:
        """Оценить влияние сообщения на отношения с другими участниками."""
        text = (message or "").lower()
        impacts: Dict[str, float] = {}

        delta = 0.0
        for pattern, weight in POSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                delta += weight
                break
        for pattern, weight in NEGATIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                delta += weight
                break

        if abs(delta) < 0.05:
            return None

        # Распределяем влияние на упомянутых участников
        mentioned = [p for p in participants if p != sender and p.lower() in text]
        if not mentioned:
            mentioned = [p for p in participants if p != sender]

        if not mentioned:
            return None

        per_agent = delta / len(mentioned)
        for p in mentioned:
            impacts[p] = per_agent * self.influence_coefficient

        reason = "согласие" if delta > 0 else "несогласие"
        logger.debug(
            "heuristic_analyzer sender=%s delta=%.2f impacts=%s",
            sender, delta, impacts,
        )
        return AnalysisResult(
            message_id=message_id or f"{sender}_{datetime.now().timestamp()}",
            sender=sender,
            content=message,
            timestamp=datetime.now(),
            impacts=impacts,
            sentiment=1.0 if delta > 0 else -1.0,
            emotions={},
            reason=reason,
            metadata={"source": "heuristic", "participants": participants},
        )
