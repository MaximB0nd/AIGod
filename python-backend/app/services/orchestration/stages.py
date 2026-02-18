"""
Этапы жизненного цикла задачи (state machine).

Каждый запрос ОБЯЗАТЕЛЬНО проходит все стадии.
Без фиксированных этапов и переходов система зацикливается.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Any


class PipelineStage(Enum):
    """
    Жизненный цикл задачи. Переходы: строго по порядку.
    """
    NEW_TASK = auto()
    RETRIEVE_MEMORY = auto()
    PLAN = auto()
    DISCUSS = auto()
    SYNTHESIZE = auto()
    STORE_MEMORY = auto()
    FACT_EXTRACTION = auto()
    UPDATE_GRAPH = auto()
    DONE = auto()

    def next(self) -> Optional["PipelineStage"]:
        """Следующий этап. None если DONE."""
        stages = list(PipelineStage)
        idx = stages.index(self)
        if idx + 1 < len(stages):
            return stages[idx + 1]
        return None


@dataclass
class TaskState:
    """
    Централизованное состояние задачи. Передаётся через весь pipeline.
    """
    user_message: str
    room_id: int
    agent_names: List[str]
    stage: PipelineStage = PipelineStage.NEW_TASK

    # Результаты этапов (заполняются по мере выполнения)
    memory_context: Optional[str] = None
    plan: Optional[str] = None
    discussion_messages: List[Any] = field(default_factory=list)
    synthesized_answer: Optional[str] = None
    memory_stored: bool = False
    extracted_facts: List[Any] = field(default_factory=list)
    graph_updated: bool = False

    # Метаданные
    room: Any = None
    sender: str = "user"
    error: Optional[str] = None

    def transition_to(self, stage: PipelineStage) -> None:
        """Явный переход между этапами."""
        self.stage = stage
