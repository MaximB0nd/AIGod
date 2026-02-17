Документация модуля оркестрации агентов
📋 Содержание

    Общее описание

    Структура модуля

    Базовые компоненты

    Стратегии оркестрации

    Интеграция с YandexGPT

    Примеры использования

    API Reference

Общее описание

Модуль оркестрации агентов предназначен для управления множеством AI-агентов и организации их взаимодействия. Он позволяет создавать сложные сценарии общения между агентами, вмешательства пользователя и различные стратегии ведения диалога.

Ключевые возможности:

    Управление множеством агентов

    Различные стратегии взаимодействия

    Сохранение контекста разговора

    Интеграция с YandexGPT

    Расширяемая архитектура

Структура модуля
text

agents_orchestration/
├── __init__.py                 # Инициализация пакета
├── message_type.py              # Типы сообщений (Enum)
├── message.py                   # Модель сообщения
├── context.py                   # Контекст разговора
├── base_strategy.py             # Базовый класс стратегии
├── orchestration_client.py      # Основной клиент
├── strategies/
│   ├── __init__.py
│   ├── circular.py              # Циркулярная стратегия
│   ├── narrator.py              # Стратегия с рассказчиком
│   └── full_context.py           # Стратегия полного контекста
└── examples/
    └── usage.py                  # Примеры использования

Базовые компоненты
1. Типы сообщений (MessageType)
python

from enum import Enum

class MessageType(Enum):
    USER = "user"              # Сообщение от пользователя
    AGENT = "agent"            # Сообщение от агента
    SYSTEM = "system"          # Системное сообщение
    NARRATOR = "narrator"      # Сообщение от рассказчика
    SUMMARIZED = "summarized"  # Сводка обсуждения

2. Модель сообщения (Message)
python

@dataclass
class Message:
    content: str                    # Текст сообщения
    type: MessageType               # Тип сообщения
    sender: str                     # Отправитель
    timestamp: datetime             # Время отправки
    metadata: Dict[str, Any]        # Метаданные
    target_agent: Optional[str]     # Целевой агент
    round_number: int                # Номер раунда

3. Контекст разговора (ConversationContext)

Хранит состояние разговора и общую память:
python

context = ConversationContext(participants=["Алиса", "Боб"])

# Добавление сообщения
context.add_message(message)

# Получение последних сообщений
recent = context.get_recent_messages(5)

# Сохранение в общей памяти
context.update_memory("key_points", ["важный вывод"])

# Получение из памяти
points = context.get_memory("key_points")

Стратегии оркестрации
1. Циркулярная стратегия (CircularStrategy)

Агенты общаются по кругу, пользователь может вмешиваться в любой момент.

Особенности:

    Агенты отвечают последовательно

    При сообщении пользователя круг начинается заново

    Отслеживаются раунды

python

from app.services.agents_orchestration.strategies import CircularStrategy

strategy = CircularStrategy(
    context=context,
    start_agent_index=0,        # С какого агента начать
    include_system_messages=True # Показывать системные сообщения
)

2. Стратегия с рассказчиком (NarratorStrategy)

Один агент (нарратор) управляет повествованием, вызывая других персонажей.

Особенности:

    Нарратор задаёт сцены и развитие сюжета

    Персонажи реагируют на ситуацию

    Автоматическое чередование наррации и диалогов

python

from app.services.agents_orchestration.strategies import NarratorStrategy

strategy = NarratorStrategy(
    context=context,
    narrator_agent="Нарратор",
    story_topic="Таинственный остров",
    narrator_interval=2,        # Тиков между наррациями
    max_agent_responses=2,       # Ответов агентов между наррациями
    randomize_agents=True        # Случайный выбор агентов
)

3. Стратегия полного контекста (FullContextStrategy)

Все агенты видят полный контекст обсуждения, формируются сводки.

Особенности:

    Общий промпт для всех

    Суммаризация каждого раунда

    Сохранение ключевых точек в памяти

python

from app.services.agents_orchestration.strategies import FullContextStrategy

strategy = FullContextStrategy(
    context=context,
    initial_prompt="Тема обсуждения",
    summary_agent="Суммаризатор",  # Кто делает сводки
    max_rounds=3,                    # Максимум раундов
    agents_per_round=2,              # Агентов в раунде
    include_system_messages=True
)

Интеграция с YandexGPT
Адаптер для YandexGPT
python

from app.services.yandex_client.yandex_agent_client import YandexAgentClient, Agent

class YandexAgentAdapter:
    """Адаптер для использования YandexGPT в оркестрации"""
    
    def __init__(self, client: YandexAgentClient):
        self.client = client
        self.agents = {}
    
    def register_agent(self, name: str, prompt: str):
        """Регистрация агента с системным промптом"""
        self.agents[name] = Agent(name, prompt)
    
    async def __call__(self, agent_name: str, session_id: str, 
                       prompt: str, context: Optional[ConversationContext] = None):
        """Отправка сообщения агенту"""
        agent = self.agents.get(agent_name)
        if not agent:
            return f"Агент {agent_name} не найден"
        
        # Добавление контекста разговора
        if context and context.history:
            recent = context.get_recent_messages(3)
            context_text = "\n".join([f"{m.sender}: {m.content}" for m in recent])
            enhanced_prompt = f"Контекст:\n{context_text}\n\nЗапрос:\n{prompt}"
        else:
            enhanced_prompt = prompt
        
        return self.client.send_message(agent, session_id, enhanced_prompt)

Пример регистрации агентов
python

# Создание адаптера
yandex_client = YandexAgentClient()
adapter = YandexAgentAdapter(yandex_client)

# Регистрация агентов
adapter.register_agent("Алиса", """
    Ты эксперт по этике ИИ. 
    Рассматривай моральные аспекты обсуждаемых тем.
""")

adapter.register_agent("Боб", """
    Ты технический эксперт.
    Объясняй возможности реализации.
""")

Примеры использования
Базовый пример
python

import asyncio
from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.strategies import CircularStrategy

async def main():
    # Создаём клиент
    agents = ["Алиса", "Боб", "Чарли"]
    client = OrchestrationClient(agents, your_agent_adapter)
    
    # Устанавливаем стратегию
    strategy = CircularStrategy(client.context)
    client.set_strategy(strategy)
    
    # Обработчик сообщений
    async def on_message(message):
        print(f"{message.sender}: {message.content}")
    
    client.on_message(on_message)
    
    # Запускаем
    await client.start(max_ticks=10)
    
    # Отправляем сообщение пользователя
    await client.send_user_message("Привет, агенты!")

asyncio.run(main())

Полный пример с YandexGPT
python

import asyncio
from app.services.yandex_client.yandex_agent_client import YandexAgentClient
from app.services.agents_orchestration import OrchestrationClient
from app.services.agents_orchestration.strategies import NarratorStrategy

class YandexAdapter:
    # ... реализация адаптера ...

async def story_example():
    # Инициализация
    yandex = YandexAgentClient()
    adapter = YandexAdapter(yandex)
    
    # Регистрация агентов
    adapter.register_agent("Нарратор", "Ты рассказчик, веди историю")
    adapter.register_agent("Герой", "Ты главный герой")
    
    # Создание клиента
    client = OrchestrationClient(
        agents=["Нарратор", "Герой"],
        chat_service=adapter
    )
    
    # Настройка стратегии
    strategy = NarratorStrategy(
        client.context,
        narrator_agent="Нарратор",
        story_topic="Приключения в космосе"
    )
    client.set_strategy(strategy)
    
    # Запуск
    await client.start(max_ticks=20)

API Reference
OrchestrationClient
python

class OrchestrationClient:
    def __init__(self, agents: List[str], chat_service: Callable):
        """
        agents: список имён агентов
        chat_service: функция для отправки сообщений агентам
        """
    
    def set_strategy(self, strategy: BaseStrategy):
        """Установка стратегии оркестрации"""
    
    def on_message(self, callback: Callable[[Message], Awaitable[None]]):
        """Установка обработчика сообщений"""
    
    async def start(self, max_ticks: Optional[int] = None):
        """Запуск оркестрации"""
    
    async def stop(self):
        """Остановка оркестрации"""
    
    async def send_user_message(self, message: str):
        """Отправка сообщения от пользователя"""
    
    def get_statistics(self) -> dict:
        """Получение статистики"""

ConversationContext
python

class ConversationContext:
    def add_message(self, message: Message):
        """Добавить сообщение в историю"""
    
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """Получить последние n сообщений"""
    
    def get_messages_by_type(self, msg_type: MessageType) -> List[Message]:
        """Получить сообщения определённого типа"""
    
    def update_memory(self, key: str, value: Any):
        """Сохранить в общей памяти"""
    
    def get_memory(self, key: str, default=None) -> Any:
        """Получить из общей памяти"""
    
    def export_conversation(self) -> str:
        """Экспортировать разговор в текст"""

BaseStrategy (для создания своих стратегий)
python

class BaseStrategy(ABC):
    def __init__(self, context: ConversationContext):
        self.context = context
    
    @abstractmethod
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        """Выполняется каждый тик"""
        pass
    
    @abstractmethod
    async def handle_user_message(self, message: str) -> List[Message]:
        """Обработка сообщения пользователя"""
        pass
    
    async def on_start(self):
        """При старте стратегии"""
        pass
    
    async def on_stop(self):
        """При остановке стратегии"""
        pass

Советы по использованию
1. Выбор стратегии
Стратегия	Когда использовать
Circular	Простой диалог, мозговой штурм
Narrator	Создание историй, ролевые игры
FullContext	Сложные обсуждения, требующие анализа
2. Оптимизация

    Устанавливайте max_ticks для ограничения времени работы

    Используйте max_rounds в стратегиях для предотвращения бесконечных циклов

    Регулярно очищайте историю при длительных сессиях

3. Обработка ошибок
python

try:
    await client.start(max_ticks=10)
except Exception as e:
    print(f"Ошибка: {e}")
    await client.stop()

4. Мониторинг
python

# Получение статистики
stats = client.get_statistics()
print(f"Всего сообщений: {stats['context']['total_messages']}")
print(f"Текущая стратегия: {stats['strategy']['name']}")

Расширение модуля
Создание своей стратегии
python

from app.services.agents_orchestration import BaseStrategy, Message

class MyStrategy(BaseStrategy):
    def __init__(self, context):
        super().__init__(context)
        self.counter = 0
    
    async def tick(self, agents):
        if self.counter >= 5:
            return None
        
        message = Message(
            content=f"Тик {self.counter}",
            type=MessageType.SYSTEM,
            sender="System"
        )
        self.counter += 1
        return [message]
    
    async def handle_user_message(self, message):
        return [Message(
            content=f"Получено: {message}",
            type=MessageType.SYSTEM,
            sender="System"
        )]

Заключение

Модуль оркестрации агентов предоставляет гибкую и расширяемую архитектуру для управления множеством AI-агентов. Основные преимущества:

    ✅ Модульность - легко добавлять новые стратегии

    ✅ Интеграция с YandexGPT - готовая интеграция

    ✅ Управление контекстом - сохранение истории и общей памяти

    ✅ Гибкость - адаптация под любые сценарии

    ✅ Мониторинг - статистика и логирование

Для вопросов и предложений обращайтесь к разработчикам модуля.
