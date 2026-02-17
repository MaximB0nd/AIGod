#!/usr/bin/env python
"""
Пример использования модуля оркестрации агентов с YandexGPT.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import signal

# Добавляем корень проекта в путь
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"✅ Добавлен корень проекта: {project_root}")

from app.services.agents_orchestration import (
    OrchestrationClient,
    ConversationContext,
    Message,
    MessageType
)
from app.services.agents_orchestration.strategies import (
    CircularStrategy,
    NarratorStrategy,
    FullContextStrategy
)

# Импорт Yandex клиента
from app.services.yandex_client.yandex_agent_client import YandexAgentClient, Agent


class YandexAgentAdapter:
    """
    Адаптер для использования YandexAgentClient в оркестрации.
    """
    def __init__(self, client: YandexAgentClient):
        self.client = client
        self.agents: dict[str, Agent] = {}
        self.session_counter = 0
    
    def register_agent(self, name: str, prompt: str):
        """Регистрация агента"""
        self.agents[name] = Agent(name, prompt)
        print(f"  ✅ Агент '{name}' зарегистрирован")
    
    def _create_session_id(self, strategy_name: str) -> str:
        """Создание уникального ID сессии"""
        self.session_counter += 1
        return f"{strategy_name}_session_{self.session_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def __call__(self, agent_name: str, session_id: str, prompt: str, 
                       context: Optional[ConversationContext] = None):
        """
        Отправка сообщения агенту через YandexAgentClient.
        """
        # Получаем агента
        agent = self.agents.get(agent_name)
        if not agent:
            return f"[{agent_name}] Агент не найден"
        
        # Добавляем контекст из оркестрации в промпт
        if context and context.history:
            recent = context.get_recent_messages(5)
            context_text = "\n".join([
                f"{m.sender}: {m.content}" for m in recent
            ])
            
            enhanced_prompt = f"""
Контекст разговора (последние сообщения):
{context_text}

Текущая задача/запрос:
{prompt}

Продолжи разговор естественно, учитывая контекст и свою роль.
"""
        else:
            enhanced_prompt = prompt
        
        # Используем переданный session_id или создаем новый
        actual_session_id = session_id or self._create_session_id("unknown")
        
        # Отправляем через YandexAgentClient
        response = self.client.send_message(agent, actual_session_id, enhanced_prompt)
        
        # Небольшая задержка
        await asyncio.sleep(0.5)
        
        return response


async def message_handler(message: Message):
    """Обработчик сообщений"""
    icons = {
        MessageType.USER: "👤",
        MessageType.AGENT: "🤖", 
        MessageType.SYSTEM: "⚙️",
        MessageType.NARRATOR: "📖",
        MessageType.SUMMARIZED: "📝"
    }
    
    icon = icons.get(message.type, "📌")
    time = message.timestamp.strftime("%H:%M:%S")
    
    type_names = {
        MessageType.USER: "Пользователь",
        MessageType.AGENT: "Агент",
        MessageType.SYSTEM: "Система",
        MessageType.NARRATOR: "🎭 Рассказчик",
        MessageType.SUMMARIZED: "📊 Сводка"
    }
    
    type_name = type_names.get(message.type, str(message.type))
    
    print(f"{time} {icon} {type_name} {message.sender}: {message.content}")
    
    # Сохраняем в файл
    log_path = Path(__file__).parent / "разговор_лог.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time}] {type_name} {message.sender}: {message.content}\n")


async def setup_agents():
    """Настройка агентов с промптами"""
    
    print("\n📝 Регистрация агентов...")
    
    # Создаем клиент Yandex
    try:
        yandex_client_instance = YandexAgentClient()
        print("  ✅ YandexAgentClient создан")
    except Exception as e:
        print(f"  ❌ Ошибка создания YandexAgentClient: {e}")
        raise
    
    # Создаем адаптер
    adapter = YandexAgentAdapter(yandex_client_instance)
    
    # Регистрируем агентов
    agents_config = [
        ("Алиса", "эксперт по этике ИИ, рассматриваешь моральные аспекты"),
        ("Боб", "технический эксперт, объясняешь возможности реализации"),
        ("Чарли", "специалист по практике, фокусируешься на реальных кейсах"),
        ("Нарратор", "рассказчик, создаешь увлекательное повествование"),
        ("Герой", "смелый искатель приключений, полный энтузиазма"),
        ("Злодей", "таинственный антагонист с хитрыми планами"),
        ("Мудрец", "старый хранитель знаний, говоришь загадками"),
        ("Учёный", "исследователь, опираешься на научные данные"),
        ("Философ", "мыслитель, задаешь глубокие вопросы"),
        ("Инженер", "практик, предлагаешь конкретные решения"),
        ("Суммаризатор", "аналитик, подводишь итоги дискуссий")
    ]
    
    for name, role in agents_config:
        prompt = f"Ты {name}, {role}. Отвечай развернуто, но по существу."
        adapter.register_agent(name, prompt)
    
    print(f"  ✅ Всего зарегистрировано агентов: {len(adapter.agents)}\n")
    return adapter


async def run_strategy_with_timeout(client, max_ticks: int, timeout: int, strategy_name: str):
    """Запуск стратегии с таймаутом"""
    try:
        # Запускаем клиент
        task = asyncio.create_task(client.start(max_ticks=max_ticks))
        
        # Ждем завершения или таймаута
        await asyncio.wait_for(task, timeout=timeout)
        
    except asyncio.TimeoutError:
        print(f"⏰ Таймаут {strategy_name} ({timeout}с), принудительно останавливаем...")
        await client.stop()
    except Exception as e:
        print(f"❌ Ошибка в {strategy_name}: {e}")
        await client.stop()
    
    print(f"✅ {strategy_name} завершена")
    await asyncio.sleep(2)  # Пауза между стратегиями


async def test_circular(agent_adapter):
    """Тест циркулярной стратегии"""
    print("\n🔄 Тестирование циркулярной стратегии")
    print("=" * 60)
    
    agents = ["Алиса", "Боб", "Чарли"]
    client = OrchestrationClient(agents, agent_adapter)
    client.on_message(message_handler)
    
    strategy = CircularStrategy(client.context)
    client.set_strategy(strategy)
    
    print("📌 Отправляем сообщения пользователя...")
    
    # Запускаем клиент в фоне
    client_task = asyncio.create_task(client.start(max_ticks=8))
    
    # Отправляем сообщения с задержками
    await asyncio.sleep(2)
    await client.send_user_message("Давайте обсудим этические аспекты искусственного интеллекта")
    
    await asyncio.sleep(4)
    await client.send_user_message("А как насчёт практического применения?")
    
    await asyncio.sleep(4)
    await client.send_user_message("Какие технологии нужны для этого?")
    
    # Ждем завершения с таймаутом
    try:
        await asyncio.wait_for(client_task, timeout=30)
    except asyncio.TimeoutError:
        print("⏰ Таймаут циркулярной стратегии, останавливаем...")
        await client.stop()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await client.stop()


async def test_narrator(agent_adapter):
    """Тест стратегии с рассказчиком"""
    print("\n📖 Тестирование стратегии с рассказчиком")
    print("=" * 60)
    
    agents = ["Нарратор", "Герой", "Злодей", "Мудрец"]
    client = OrchestrationClient(agents, agent_adapter)
    client.on_message(message_handler)
    
    story_topic = "Таинственный остров появляется в Тихом океане"
    strategy = NarratorStrategy(
        client.context,
        narrator_agent="Нарратор",
        story_topic=story_topic,
        narrator_interval=2
    )
    client.set_strategy(strategy)
    
    print(f"📌 Тема истории: {story_topic}")
    
    # Запускаем с таймаутом
    await run_strategy_with_timeout(client, max_ticks=8, timeout=40, strategy_name="Стратегия рассказчика")


async def test_full_context(agent_adapter):
    """Тест стратегии полного контекста"""
    print("\n🌐 Тестирование стратегии полного контекста")
    print("=" * 60)
    
    agents = ["Учёный", "Философ", "Инженер", "Суммаризатор"]
    client = OrchestrationClient(agents, agent_adapter)
    client.on_message(message_handler)
    
    initial_prompt = "Как мы можем достичь устойчивой энергетики для всех?"
    strategy = FullContextStrategy(
        client.context,
        initial_prompt=initial_prompt,
        summary_agent="Суммаризатор",
        max_rounds=2,  # Уменьшим для теста
        agents_per_round=2
    )
    client.set_strategy(strategy)
    
    print(f"📌 Тема обсуждения: {initial_prompt}")
    
    # Запускаем с таймаутом
    await run_strategy_with_timeout(client, max_ticks=6, timeout=40, strategy_name="Стратегия полного контекста")
    
    # Показываем результаты
    print("\n📊 Итоги дискуссии:")
    key_points = client.context.get_memory("key_points", [])
    if key_points:
        for i, point in enumerate(key_points, 1):
            print(f"  {i}. {point[:100]}...")
    else:
        print("  Нет ключевых точек")


async def shutdown(sig, loop):
    """Корректное завершение при Ctrl+C"""
    print(f"\n\n🛑 Получен сигнал {sig.name}, завершаю работу...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    """Главная функция"""
    # Настройка обработки сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
    
    print("🚀 Запуск примеров оркестрации агентов с YandexGPT")
    print(f"📁 Корень проекта: {project_root}")
    print("Нажмите Ctrl+C для остановки\n")
    
    # Очищаем лог
    log_path = Path(__file__).parent / "разговор_лог.txt"
    open(log_path, "w", encoding="utf-8").close()
    
    try:
        # Настраиваем агентов
        agent_adapter = await setup_agents()
        
        # Последовательно запускаем все стратегии
        print("\n" + "="*60)
        print("ТЕСТ 1: Циркулярная стратегия")
        print("="*60)
        await test_circular(agent_adapter)
        
        print("\n" + "="*60)
        print("ТЕСТ 2: Стратегия с рассказчиком")
        print("="*60)
        await test_narrator(agent_adapter)
        
        print("\n" + "="*60)
        print("ТЕСТ 3: Стратегия полного контекста")
        print("="*60)
        await test_full_context(agent_adapter)
        
        print("\n✅ Все тесты успешно завершены!")
        print(f"📁 Полный лог сохранен в: {log_path}")
        
    except asyncio.CancelledError:
        print("\n\n👋 Программа остановлена пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n📊 Программа завершена")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 До свидания!")
