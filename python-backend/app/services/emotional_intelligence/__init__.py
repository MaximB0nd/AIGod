"""
Модуль эмоционального интеллекта для агентов
"""
from .models import (
    EmotionalState, EmotionalProfile, EmotionAnalysisResult,
    EmotionType, EmotionalContext
)
from .analyzer import EmotionAnalyzer
from .manager import EmotionalIntelligenceManager
from .events import EventType, EmotionalEvent
from .integration import EmotionalOrchestrationIntegration

__version__ = "1.0.0"

__all__ = [
    # Основные классы
    'EmotionalIntelligenceManager',
    'EmotionAnalyzer',
    'EmotionalOrchestrationIntegration',
    
    # Модели
    'EmotionalState',
    'EmotionalProfile',
    'EmotionAnalysisResult',
    'EmotionalContext',
    'EmotionType',
    
    # События
    'EventType',
    'EmotionalEvent',
    
    # Версия
    '__version__'
]
