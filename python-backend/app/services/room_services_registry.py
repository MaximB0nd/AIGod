"""
Реестр сервисов для комнат: память, эмоции.
Создаёт и хранит экземпляры на комнату для совместной работы с LLM и оркестрацией.
"""
from typing import Optional

# Memory
_memory_managers: dict[int, "MemoryManager"] = {}
_memory_integrations: dict[int, "MemoryOrchestrationIntegration"] = {}

# Emotional
_emotional_managers: dict[int, "EmotionalIntelligenceManager"] = {}
_emotional_integrations: dict[int, "EmotionalOrchestrationIntegration"] = {}


def get_memory_integration(room) -> Optional["MemoryOrchestrationIntegration"]:
    """
    Получить интеграцию памяти для комнаты.

    При доступном ChromaDB (CHROMA_PERSIST_DIR) использует векторное хранилище
    для долгосрочной памяти комнаты. Иначе — только short-term.
    """
    room_id = room.id
    if room_id in _memory_integrations:
        return _memory_integrations[room_id]
    try:
        from app.services.context_memory.memory_manager import MemoryManager
        from app.services.context_memory.integration import MemoryOrchestrationIntegration
        from app.services.context_memory.models import ImportanceLevel

        vector_store = None
        try:
            from app.config import config
            persist_dir = config.CHROMA_PERSIST_DIR
        except Exception:
            persist_dir = __import__("os").environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
        try:
            from app.services.context_memory.vector_store import (
                VectorMemoryStore,
                CHROMA_AVAILABLE,
            )
            if CHROMA_AVAILABLE and persist_dir:
                vector_store = VectorMemoryStore(
                    collection_name=f"room_memory_{room_id}",
                    persist_directory=persist_dir,
                )
        except Exception as e:
            vector_store = None
            # ChromaDB может падать из-за np.float_ в NumPy 2.0 — работаем без vector_store

        manager = MemoryManager(
            vector_store=vector_store,
            summarizer=None,
            conversation_id=f"room_{room_id}",
        )
        integration = MemoryOrchestrationIntegration(
            memory_manager=manager,
            auto_summarize=False,
            importance_threshold=ImportanceLevel.MEDIUM,
        )
        _memory_managers[room_id] = manager
        _memory_integrations[room_id] = integration
        return integration
    except Exception as e:
        print(f"Memory integration init failed for room {room_id}: {e}")
        return None


def get_emotional_integration(room) -> Optional["EmotionalOrchestrationIntegration"]:
    """Получить интеграцию эмоций для комнаты (без LLM-анализа, только состояние)."""
    room_id = room.id
    if room_id in _emotional_integrations:
        return _emotional_integrations[room_id]
    try:
        from app.services.emotional_intelligence import EmotionalIntelligenceManager
        from app.services.emotional_intelligence.integration import EmotionalOrchestrationIntegration

        manager = EmotionalIntelligenceManager(analyzer=None)
        agent_names = [a.name for a in room.agents]
        manager.register_entities(agent_names)
        integration = EmotionalOrchestrationIntegration(
            emotional_manager=manager,
            auto_analyze=False,
        )
        _emotional_managers[room_id] = manager
        _emotional_integrations[room_id] = integration
        return integration
    except Exception as e:
        print(f"Emotional integration init failed for room {room_id}: {e}")
        return None


def ensure_emotional_agents_registered(room, integration) -> None:
    """Обновить список агентов в эмоциональном менеджере при изменении комнаты."""
    if not integration:
        return
    for a in room.agents:
        if a.name not in integration.manager.states:
            integration.manager.register_entity(a.name)


def cleanup_room(room_id: int) -> None:
    """Очистить сервисы комнаты (при удалении комнаты)."""
    _memory_managers.pop(room_id, None)
    _memory_integrations.pop(room_id, None)
    _emotional_managers.pop(room_id, None)
    _emotional_integrations.pop(room_id, None)
