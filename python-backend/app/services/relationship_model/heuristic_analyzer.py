"""
Эвристический анализатор отношений без LLM.

Обновляет граф по ключевым словам и по участию в диалоге (даже при коротком общении).
"""
import re
import logging
from typing import Dict, List, Optional

from .models import AnalysisResult
from datetime import datetime

logger = logging.getLogger("aigod.relationship.heuristic")

# Базовое влияние при участии в диалоге (любое сообщение немного сближает)
PARTICIPATION_DELTA = 0.06
# Влияние при ответе на предыдущего спикера
RESPONSE_TO_PREVIOUS_DELTA = 0.08

# Ключевые слова: фраза -> сила влияния
POSITIVE_PATTERNS = [
    (r"\bсогласен\b", 0.18),
    (r"\bподдерживаю\b", 0.18),
    (r"\bотлично\b", 0.12),
    (r"\bправильно\b", 0.12),
    (r"\bхорошо\b", 0.1),
    (r"\bда\s*,?\s*(именно|верно)", 0.12),
    (r"\bполностью\s+согласен\b", 0.25),
    (r"\bточно\b", 0.1),
    (r"\bинтересно\b", 0.08),
    (r"\bспасибо\b", 0.1),
    (r"\bблагодар\b", 0.12),
]
NEGATIVE_PATTERNS = [
    (r"\bне\s+согласен\b", -0.18),
    (r"\bспорно\b", -0.12),
    (r"\bнеправильно\b", -0.14),
    (r"\bнесогласен\b", -0.18),
    (r"\bневерно\b", -0.14),
    (r"\bабсурд\b", -0.15),
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
        """Оценить влияние сообщения на отношения. Всегда возвращает результат при любом сообщении."""
        text = (message or "").lower()
        impacts: Dict[str, float] = {}
        delta = 0.0
        reason = "участие в диалоге"

        # 1. Ключевые слова согласия/несогласия
        for pattern, weight in POSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                delta += weight
                reason = "согласие"
                break
        for pattern, weight in NEGATIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                delta += weight
                reason = "несогласие"
                break

        # 2. Упоминания имён — усиление влияния на упомянутых
        mentioned = [p for p in participants if p != sender and p.lower() in text]
        if not mentioned:
            mentioned = [p for p in participants if p != sender]

        if mentioned:
            if abs(delta) >= 0.05:
                per_agent = delta / len(mentioned) * self.influence_coefficient
            else:
                per_agent = PARTICIPATION_DELTA * self.influence_coefficient
            for p in mentioned:
                impacts[p] = impacts.get(p, 0) + per_agent
        else:
            # 3. Даже без ключевых слов — участие сближает со всеми
            participation = PARTICIPATION_DELTA * self.influence_coefficient
            for p in participants:
                if p != sender:
                    impacts[p] = participation

        # 4. Контекст: последнее сообщение — кто говорил до этого (ответ на него)
        if context and isinstance(context, list) and len(context) >= 1:
            last = str(context[-1]) if context else ""
            for p in participants:
                if p != sender and (p in last or p.lower() in last.lower()):
                    impacts[p] = impacts.get(p, 0) + RESPONSE_TO_PREVIOUS_DELTA * self.influence_coefficient
                    break

        if not impacts:
            return None

        logger.debug(
            "heuristic_analyzer sender=%s impacts=%s reason=%s",
            sender, impacts, reason,
        )
        return AnalysisResult(
            message_id=message_id or f"{sender}_{datetime.now().timestamp()}",
            sender=sender,
            content=message,
            timestamp=datetime.now(),
            impacts=impacts,
            sentiment=1.0 if delta > 0 else (-1.0 if delta < 0 else 0.5),
            emotions={},
            reason=reason,
            metadata={"source": "heuristic", "participants": participants},
        )
