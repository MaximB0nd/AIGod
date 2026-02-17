from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
import uuid

class MemoryType(str, Enum):
    """Тип памяти"""
    SHORT_TERM = "short_term"      # краткосрочная (текущий разговор)
    LONG_TERM = "long_term"        # долгосрочная (важные моменты)
    EPISODIC = "episodic"          # эпизодическая (конкретные события)
    SEMANTIC = "semantic"          # семантическая (факты, знания)
    PROCEDURAL = "procedural"      # процедурная (как делать)

class ImportanceLevel(str, Enum):
    """Уровень важности"""
    CRITICAL = "critical"      # критично важно
    HIGH = "high"               # очень важно
    MEDIUM = "medium"           # средне важно
    LOW = "low"                 # мало важно
    TRIVIAL = "trivial"         # неважно

@dataclass
class MemoryItem:
    """Элемент памяти"""
    id: str
    content: str
    type: MemoryType
    importance: ImportanceLevel
    timestamp: datetime
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # ссылки на другие memory_id
    
    # Для эпизодической памяти
    participants: List[str] = field(default_factory=list)
    location: Optional[str] = None
    
    # Срок жизни (для краткосрочной)
    ttl: Optional[int] = None  # в секундах
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "type": self.type.value,
            "importance": self.importance.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
            "participants": self.participants
        }
    
    def is_expired(self) -> bool:
        """Проверить, истёк ли срок жизни"""
        if self.ttl:
            age = (datetime.now() - self.timestamp).seconds
            return age > self.ttl
        return False

@dataclass
class ConversationChunk:
    """Чанк разговора для суммаризации"""
    chunk_id: str
    conversation_id: str
    messages: List[Dict]
    start_time: datetime
    end_time: datetime
    participants: List[str]
    token_count: int
    
    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "participants": self.participants,
            "token_count": self.token_count
        }

@dataclass
class Summary:
    """Результат суммаризации"""
    summary_id: str
    original_chunks: List[str]  # ID чанков
    content: str
    created_at: datetime
    token_count: int
    
    # Ключевые моменты
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)  # принятые решения
    action_items: List[str] = field(default_factory=list)  # что нужно сделать
    
    # Метрики
    compression_ratio: float = 0.0  # во сколько раз сжато
    quality_score: float = 0.0  # оценка качества (0-1)
    
    # Для иерархической суммаризации
    parent_summary: Optional[str] = None
    child_summaries: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "summary_id": self.summary_id,
            "created_at": self.created_at.isoformat(),
            "content": self.content,
            "key_points": self.key_points[:5],  # топ-5
            "decisions": self.decisions,
            "action_items": self.action_items,
            "compression_ratio": self.compression_ratio,
            "token_count": self.token_count
        }

@dataclass
class MemoryStats:
    """Статистика памяти"""
    total_items: int
    total_tokens: int
    memory_by_type: Dict[MemoryType, int]
    memory_by_importance: Dict[ImportanceLevel, int]
    average_importance: float
    oldest_memory: datetime
    newest_memory: datetime
    vector_store_size: int  # количество векторов

@dataclass
class ContextWindow:
    """Текущее окно контекста"""
    max_tokens: int
    current_tokens: int = 0
    messages: List[Dict] = field(default_factory=list)
    summaries: List[Summary] = field(default_factory=list)
    
    def add_message(self, message: Dict, tokens: int):
        """Добавить сообщение"""
        self.messages.append(message)
        self.current_tokens += tokens
        
        # Если превысили лимит, нужно сжимать
        return self.current_tokens > self.max_tokens
    
    def get_context(self) -> str:
        """Получить контекст для промпта"""
        parts = []
        
        # Сначала суммаризации
        if self.summaries:
            parts.append("=== Ранее в разговоре ===")
            for summary in self.summaries[-2:]:  # последние 2 суммаризации
                parts.append(summary.content)
            parts.append("")
        
        # Потом последние сообщения
        if self.messages:
            parts.append("=== Текущий разговор ===")
            for msg in self.messages[-10:]:  # последние 10 сообщений
                parts.append(f"{msg['sender']}: {msg['content']}")
        
        return "\n".join(parts)
    
    def should_summarize(self) -> bool:
        """Проверить, нужно ли делать суммаризацию"""
        return len(self.messages) > 20 or self.current_tokens > self.max_tokens * 0.8
