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

## Оркестрация

Модуль `app/services/agents_orchestration/` подключён к YandexGPT через `YandexAgentAdapter` (см. `examples/usage.py`). Для фоновой циркулярной оркестрации агентов в комнате можно использовать `OrchestrationClient` + `CircularStrategy` — это отдельный слой поверх текущих эндпоинтов.

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
