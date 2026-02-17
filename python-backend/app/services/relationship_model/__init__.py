"""
Система управления отношениями между агентами
"""
from .models import Relationship, RelationshipGraph, AnalysisResult, RelationshipType
from .analyzer import RelationshipAnalyzer
from .manager import RelationshipManager
from .events import EventType, RelationshipEvent, EventEmitter
from .integration import OrchestrationIntegration

__version__ = "1.0.0"

__all__ = [
    # Основные классы
    'RelationshipManager',
    'RelationshipAnalyzer',
    'OrchestrationIntegration',
    
    # Модели
    'Relationship',
    'RelationshipGraph',
    'AnalysisResult',
    'RelationshipType',
    
    # События
    'EventType',
    'RelationshipEvent',
    'EventEmitter',
    
    # Версия
    '__version__'
]
