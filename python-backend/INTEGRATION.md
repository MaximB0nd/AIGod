# Интеграция: эндпоинты + модули YandexGPT/оркестрации

## Сделано

### 1. Связка LLM с POST `/api/rooms/{roomId}/agents/{agentId}/messages`

- При отправке сообщения агенту теперь вызывается **YandexGPT** через `YandexAgentClient`
- Ответ агента сохраняется в БД и возвращается в `agentResponse`
- Сообщение и ответ рассылаются в WebSocket `/api/rooms/{roomId}/chat`

### 2. Модули другого разработчика

- **Импорты**: `yandex_client` переведён на `app.services.yandex_client.*`
- **ChromaDB**: сделан опциональным (память отключается при ошибке инициализации)
- **Адаптер**: `Agent.personality` (БД) → `prompt` для YandexAgentClient

### 3. Конфигурация

Добавлены переменные в `app/config.py`:
- `YANDEX_CLOUD_FOLDER` — folder_id в Yandex Cloud
- `YANDEX_CLOUD_API_KEY` — API key

В `.env` задать:
```
YANDEX_CLOUD_FOLDER=your_folder_id
YANDEX_CLOUD_API_KEY=Api-Key your_key
```

### 4. Зависимости

- В `requirements.txt` добавлен `yandex-ai-studio-sdk`
- ChromaDB (опционально) — для памяти агентов

## Использование

1. `pip install -r requirements.txt` (включая yandex-ai-studio-sdk)
2. Настроить `.env` с ключами Yandex
3. POST `/api/rooms/{roomId}/agents/{agentId}/messages` с `{"text": "...", "sender": "user"}` возвращает ответ агента

## Тип оркестрации комнаты

При создании комнаты клиент передаёт `orchestration_type`:
- `single` (по умолчанию) — пользователь общается с одним агентом
- `circular` — агенты общаются по кругу
- `narrator` — агент-рассказчик
- `full_context` — полный контекст для всех

Тип сохраняется в Room и передаётся в ChatService при каждом сообщении → YandexAgentClient добавляет контекст в промпт (например, для circular: «ты участвуешь в циркулярном разговоре»).

**API:** POST `/api/rooms` — `{"name": "...", "orchestration_type": "circular"}`, PATCH `/api/rooms/{id}` — `{"orchestration_type": "narrator"}`

## Оркестрация (полный цикл)

Модуль `app/services/agents_orchestration/` подключён к YandexGPT через `YandexAgentAdapter` (см. `examples/usage.py`). Для фоновой циркулярной оркестрации агентов в комнате используется `OrchestrationClient` + `CircularStrategy` — при POST message в комнату с `orchestration_type != "single"` сообщение передаётся в очередь оркестрации, ответы приходят via WebSocket.

## Интеграция сервисов (relationship, memory, emotions)

### Обогащение промптов
- **llm_service.get_agent_response** — при вызове с `room` добавляет контекст отношений (relationship_model) в характер агента
- **YandexAgentAdapter** (оркестрация) — обёрнут в `_RelationshipEnhancingAdapter`, дополняет промпт отношениями перед вызовом LLM

### Эндпоинты
- **GET /api/rooms/{id}/relationship-model** — граф отношений, типы (friendly/hostile), статистика
- **GET /api/rooms/{id}/emotional-state** — эмоциональное состояние агентов комнаты
- **GET /api/rooms/{id}/context-memory** — сводка контекста разговора (модуль context_memory)

### Обновление при сообщениях
После POST message (режим single) в фоне вызываются `get_memory_integration` и `get_emotional_integration` — сообщения пользователя и ответа агента сохраняются в память; эмоциональный менеджер обновляет состояния.

### Зависимости
- **relationship_model** — без внешних зависимостей, синхронизируется с БД (таблица relationships)
- **emotional_intelligence** — работает без LLM-анализатора (ручное состояние)
- **context_memory** — без ChromaDB использует только short-term (in-memory)

## Тесты

```bash
pytest tests/ -v
```

| Файл | Что проверяет |
|------|---------------|
| `tests/test_llm_service.py` | AgentPromptAdapter, fallback при отсутствии ключей, вызов ChatService (мок) |
| `tests/test_message_endpoint_integration.py` | POST messages → LLM → сохранение в БД → broadcast в WebSocket |
| `tests/test_yandex_client_chain.py` | ChatService → CharacterAgent → YandexAgentClient (мок) |
| `tests/test_orchestration.py` | OrchestrationClient, CircularStrategy, ConversationContext, связь с async chat_service |

Тесты используют `SQLITE_DB_PATH=:memory:` и моки для Yandex API — реальные запросы не выполняются.

**Примечание:** Эндпоинтов, использующих оркестрацию, в API пока нет — модуль работает как standalone (`run_orchestration.py`). Тесты проверяют сам модуль оркестрации и интеграцию с chat_service.
