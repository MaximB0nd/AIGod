"""
Модуль когнитивных процессов агента - планирование, рефлексия, принятие решений
"""
from .models import (
    Thought, ThoughtType, Plan, PlanStatus,
    Reflection, ReflectionType, Decision, Goal,
    CognitiveState
)
from .memory_stream import MemoryStream, ThoughtProcessor
from .planner import Planner
from .reflector import Reflector
from .goal_manager import GoalManager
from .decision_maker import DecisionMaker
from .integration import CognitiveIntegration

__version__ = "1.0.0"

__all__ = [
    # Основные классы
    'CognitiveIntegration',
    'MemoryStream',
    'ThoughtProcessor',
    'Planner',
    'Reflector',
    'GoalManager',
    'DecisionMaker',
    
    # Модели
    'Thought',
    'ThoughtType',
    'Plan',
    'PlanStatus',
    'Reflection',
    'ReflectionType',
    'Decision',
    'Goal',
    'CognitiveState',
    
    # Версия
    '__version__'
]
