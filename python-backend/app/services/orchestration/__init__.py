"""
Orchestration pipeline — единый движок выполнения.

Жизненный цикл задачи (обязательные этапы):
NEW_TASK → RETRIEVE_MEMORY → PLAN → DISCUSS → SYNTHESIZE → STORE_MEMORY → FACT_EXTRACTION → UPDATE_GRAPH → DONE

SolutionSynthesizer — FINAL DECISION MAKER (всегда после discussion).
FactExtractor — извлечение триплетов перед обновлением графа.
"""
from .stages import PipelineStage, TaskState
from .executor import PipelineExecutor
from .solution_synthesizer import SolutionSynthesizer
from .fact_extractor import FactExtractor, Fact

__all__ = ["PipelineStage", "TaskState", "PipelineExecutor", "SolutionSynthesizer", "FactExtractor", "Fact"]
