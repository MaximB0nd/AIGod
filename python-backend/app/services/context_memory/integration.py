"""
Интеграция системы памяти с модулем оркестрации
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from .memory_manager import MemoryManager
from .models import ImportanceLevel, MemoryType

class MemoryOrchestrationIntegration:
    """
    Интеграция системы памяти с OrchestrationClient
    """
    
    def __init__(self, 
                 memory_manager: MemoryManager,
                 auto_summarize: bool = True,
                 importance_threshold: ImportanceLevel = ImportanceLevel.MEDIUM):
        
        self.memory_manager = memory_manager
        self.auto_summarize = auto_summarize
        self.importance_threshold = importance_threshold
        
        # Статистика интеграции
        self.stats = {
            "messages_processed": 0,
            "memories_created": 0,
            "context_refreshes": 0
        }
    
    async def on_agent_message(self,
                               message: str,
                               sender: str,
                               conversation_id: str,
                               importance: ImportanceLevel = ImportanceLevel.MEDIUM,
                               metadata: Optional[Dict] = None) -> Dict:
        """
        Обработчик сообщения от агента
        """
        self.stats["messages_processed"] += 1
        
        # Сохраняем в память
        memory = await self.memory_manager.add_message(
            content=message,
            sender=sender,
            importance=importance,
            metadata={
                "conversation_id": conversation_id,
                **(metadata or {})
            }
        )
        
        self.stats["memories_created"] += 1
        
        # Проверяем, не пора ли создать сводку
        if self.auto_summarize and len(self.memory_manager.context_window.messages) % 20 == 0:
            asyncio.create_task(self.memory_manager.create_summary())
        
        return {
            "memory_id": memory.id,
            "context_window_size": len(self.memory_manager.context_window.messages),
            "short_term_size": len(self.memory_manager.short_term),
            "needs_compression": self.memory_manager.context_window.should_summarize()
        }
    
    async def on_user_message(self,
                              message: str,
                              conversation_id: str,
                              participants: List[str]) -> Dict:
        """
        Обработчик сообщения от пользователя
        """
        # Сообщения пользователя важнее
        return await self.on_agent_message(
            message=message,
            sender="user",
            conversation_id=conversation_id,
            importance=ImportanceLevel.HIGH,
            metadata={"participants": participants}
        )
    
    def enhance_prompt_with_context(self,
                                    agent_name: str,
                                    original_prompt: str,
                                    query: Optional[str] = None) -> str:
        """Синхронная обёртка. В async предпочитайте enhance_prompt_with_context_async."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop:
            raise RuntimeError("Use enhance_prompt_with_context_async in async context")
        return asyncio.run(
            self.enhance_prompt_with_context_async(agent_name, original_prompt, query)
        )

    async def enhance_prompt_with_context_async(self,
                                               agent_name: str,
                                               original_prompt: str,
                                               query: Optional[str] = None) -> str:
        """Обогатить промпт контекстом из памяти (async)."""
        search_query = query or original_prompt
        context = await self.memory_manager.get_relevant_context_async(
            query=search_query, max_tokens=800
        )
        if context:
            return f"""
{context}

Текущий запрос:
{original_prompt}

Учитывай предыдущий контекст в своём ответе.
"""
        return original_prompt
    
    def get_conversation_summary(self) -> str:
        """Получить сводку по разговору"""
        return self.memory_manager.get_memory_summary()
    
    async def force_summarize(self) -> Optional[Dict]:
        """Принудительно создать сводку"""
        summary = await self.memory_manager.create_summary()
        if summary:
            return summary.to_dict()
        return None
    
    def search_memories(self, query: str, n_results: int = 5) -> List[Dict]:
        """Поиск в памяти"""
        import asyncio
        memories = asyncio.run(self.memory_manager.search_memory(
            query=query,
            n_results=n_results
        ))
        return [m.to_dict() for m in memories]
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "memory_stats": self.memory_manager.get_stats()
        }
