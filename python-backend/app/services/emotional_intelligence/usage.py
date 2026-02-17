#!/usr/bin/env python
"""
Пример использования модуля эмоционального интеллекта
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.emotional_intelligence import (
    EmotionalIntelligenceManager,
    EmotionAnalyzer,
    EmotionalOrchestrationIntegration,
    EmotionType,
    EventType
)

# Mock chat service
class MockChatService:
    async def __call__(self, agent_name, session_id, prompt):
        await asyncio.sleep(0.1)
        return '''
        {
            "emotions": {
                "joy": 0.8,
                "trust": 0.6,
                "anticipation": 0.4
            },
            "primary_emotion": "joy",
            "intensity": 0.7,
            "sentiment": 0.5,
            "reason": "Сообщение выражает радость и позитив"
        }
        '''

async def main():
    # 1. Создаём анализатор
    chat_service = MockChatService()
    analyzer = EmotionAnalyzer(
        chat_service=chat_service,
        analyzer_agent_name="emotion_analyzer"
    )
    await analyzer.start()
    
    # 2. Создаём менеджер
    manager = EmotionalIntelligenceManager(analyzer=analyzer)
    await manager.start()
    
    # 3. Регистрируем участников
    manager.register_entities(["Алиса", "Боб", "Чарли"])
    
    # 4. Создаём интеграцию
    integration = EmotionalOrchestrationIntegration(manager)
    
    # 5. Подписываемся на события
    def on_emotion_updated(data):
        print(f"🎭 Эмоция обновлена: {data}")
    
    manager.on(EventType.EMOTION_UPDATED, on_emotion_updated)
    
    # 6. Обрабатываем сообщения
    print("📝 Обрабатываем сообщения...")
    
    # Сообщение от Алисы
    result = await integration.on_agent_message(
        message="Я так рада вас всех видеть!",
        sender="Алиса",
        conversation_id="conv_1",
        participants=["Алиса", "Боб", "Чарли"]
    )
    print(f"Результат анализа: {result}\n")
    
    await asyncio.sleep(1)
    
    # Сообщение от Боба
    result = await integration.on_agent_message(
        message="Что-то мне грустно сегодня...",
        sender="Боб",
        conversation_id="conv_1",
        participants=["Алиса", "Боб", "Чарли"]
    )
    
    await asyncio.sleep(1)
    
    # 7. Получаем состояния
    print("\n📊 Эмоциональное состояние Алисы:")
    alice_state = integration.get_agent_emotional_state("Алиса")
    print(alice_state)
    
    print("\n📊 Эмоциональное состояние Боба:")
    bob_state = integration.get_agent_emotional_state("Боб")
    print(bob_state)
    
    # 8. Получаем атмосферу разговора
    print("\n🌐 Атмосфера разговора:")
    atmosphere = integration.get_conversation_atmosphere("conv_1")
    print(atmosphere)
    
    # 9. Обогащаем промпт
    enhanced = integration.enhance_prompt_with_emotions(
        "Алиса",
        "Что ты думаешь о сегодняшнем дне?"
    )
    print("\n📝 Обогащённый промпт:")
    print(enhanced)
    
    # 10. Эмоциональный отчёт
    print("\n📈 Эмоциональный отчёт для Боба:")
    report = integration.get_emotional_intelligence_report("Боб")
    print(report)
    
    # 11. Статистика
    print("\n📊 Статистика:")
    print(integration.get_stats())
    
    # Останавливаем
    await manager.stop()
    await analyzer.stop()

if __name__ == "__main__":
    asyncio.run(main())
