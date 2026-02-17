#!/usr/bin/env python
"""
Пример использования модуля управления контекстом
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.context_memory import (
    MemoryManager,
    MemoryOrchestrationIntegration,
    VectorMemoryStore,
    ContextSummarizer,
    ImportanceLevel
)

class MockChatService:
    async def __call__(self, agent_name, session_id, prompt):
        await asyncio.sleep(0.1)
        return '''
        {
            "content": "Разговор был о важности памяти в AI системах. Участники обсуждали как хранить контекст и когда делать суммаризацию. Было принято решение использовать иерархическую память.",
            "key_points": [
                "Память критически важна для контекста",
                "Нужна автоматическая суммаризация",
                "Иерархическая структура эффективна"
            ],
            "decisions": ["Использовать ChromaDB для векторов"],
            "action_items": ["Настроить автоматическую суммаризацию"]
        }
        '''

async def main():
    # 1. Создаём компоненты
    chat_service = MockChatService()
    
    # Векторное хранилище
    vector_store = VectorMemoryStore(
        collection_name="test_memory",
        persist_directory="./test_chroma"
    )
    
    # Суммаризатор
    summarizer = ContextSummarizer(
        chat_service=chat_service,
        summarizer_agent_name="summarizer"
    )
    await summarizer.start()
    
    # Менеджер памяти
    memory_manager = MemoryManager(
        vector_store=vector_store,
        summarizer=summarizer,
        conversation_id="test_conv_1"
    )
    await memory_manager.start()
    
    # Интеграция
    integration = MemoryOrchestrationIntegration(memory_manager)
    
    print("🚀 Тестирование системы памяти")
    print("=" * 50)
    
    # 2. Добавляем сообщения
    for i in range(25):
        result = await integration.on_agent_message(
            message=f"Сообщение {i}: обсуждаем важную тему",
            sender=f"Агент_{i % 3}",
            conversation_id="test_conv_1",
            importance=ImportanceLevel.MEDIUM if i % 5 else ImportanceLevel.HIGH
        )
        
        if i % 10 == 0:
            print(f"Добавлено {i} сообщений...")
    
    # 3. Проверяем состояние
    print("\n📊 Состояние после 25 сообщений:")
    print(integration.get_conversation_summary())
    
    # 4. Принудительная суммаризация
    print("\n📝 Создаём сводку...")
    summary = await integration.force_summarize()
    if summary:
        print(f"Сводка создана: {summary['content'][:100]}...")
    
    # 5. Поиск в памяти
    print("\n🔍 Поиск 'важная тема':")
    results = integration.search_memories("важная тема", n_results=3)
    for r in results:
        print(f"  • {r['content'][:50]}...")
    
    # 6. Обогащение промпта
    enhanced = integration.enhance_prompt_with_context(
        agent_name="Агент_0",
        original_prompt="Что мы обсуждали про память?"
    )
    print("\n📝 Обогащённый промпт:")
    print(enhanced[:200] + "...")
    
    # 7. Статистика
    print("\n📈 Статистика:")
    stats = integration.get_stats()
    print(f"Сообщений обработано: {stats['messages_processed']}")
    print(f"Воспоминаний создано: {stats['memories_created']}")
    print(f"Размер контекста: {stats['memory_stats']['context_window']['messages']} сообщений")
    
    # Останавливаем
    await memory_manager.stop()
    await summarizer.stop()

if __name__ == "__main__":
    asyncio.run(main())
