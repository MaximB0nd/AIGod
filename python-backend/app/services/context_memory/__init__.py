"""
Модуль управления контекстом и памятью с автоматической суммаризацией
"""
from .models import (
    MemoryItem, MemoryType, ImportanceLevel, 
    Summary, ContextWindow, MemoryStats
)
from .vector_store import VectorMemoryStore
from .summarizer import ContextSummarizer
from .memory_manager import MemoryManager
from .compression import ContextCompressor
from .integration import MemoryOrchestrationIntegration

__version__ = "1.0.0"

__all__ = [
    # Основные классы
    'MemoryManager',
    'MemoryOrchestrationIntegration',
    'VectorMemoryStore',
    'ContextSummarizer',
    'ContextCompressor',
    
    # Модели
    'MemoryItem',
    'MemoryType',
    'ImportanceLevel',
    'Summary',
    'ContextWindow',
    'MemoryStats',
    
    # Версия
    '__version__'
]
