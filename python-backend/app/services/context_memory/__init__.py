"""
Модуль управления контекстом и памятью с автоматической суммаризацией
"""
from .models import (
    MemoryItem, MemoryType, ImportanceLevel,
    Summary, ContextWindow, MemoryStats
)
# ChromaDB/np.float_ несовместим с NumPy 2.0 — ленивый импорт
try:
    from .vector_store import VectorMemoryStore
except Exception:
    VectorMemoryStore = None  # type: ignore
try:
    from .summarizer import ContextSummarizer
except Exception:
    ContextSummarizer = None  # type: ignore
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
