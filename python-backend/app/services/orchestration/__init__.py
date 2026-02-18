"""
Orchestration pipeline — единый движок выполнения.

Жизненный цикл задачи (обязательные этапы):
NEW_TASK → RETRIEVE_MEMORY → PLAN → DISCUSS → SYNTHESIZE → STORE_MEMORY → UPDATE_GRAPH → DONE
"""
from .stages import PipelineStage, TaskState
from .executor import PipelineExecutor

__all__ = ["PipelineStage", "TaskState", "PipelineExecutor"]
