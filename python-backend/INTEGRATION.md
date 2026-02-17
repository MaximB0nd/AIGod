# Интеграция: эндпоинты + модули YandexGPT/оркестрации

**Для фронтенда:**
- **API:** `API_DOCS.md` — полный справочник REST
- **WebSocket:** `WEBSOCKET_CLIENT.md`
- **Подключение:** `CONNECTION.md` — быстрый старт

---

## Подключение и конфигурация

### Переменные окружения (`.env`)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `YANDEX_CLOUD_FOLDER` | folder_id в Yandex Cloud | — |
| `YANDEX_CLOUD_API_KEY` | API key (можно с префиксом `Api-Key `) | — |
| `SQLITE_DB_PATH` | Путь к SQLite БД | `aigod.db` |
| `SECRET_KEY` | JWT секрет | (встроенный) |

### Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Логика агентов

### Таблица `agents` и `default_agents`
- **agents** — созданные пользователями агенты. Изначально пуста.
- **default_agents** — шаблоны (Копатыч, Гермиона и т.д.). Заполняется при первом старте из `app/data/default_agents_data.py`.

### Создание агента по шаблону
1. `GET /api/default-agents` — список шаблонов
2. `GET /api/default-agents/{id}` — данные для формы (name, character, avatar)
3. `POST /api/rooms/{roomId}/agents` с `{name, character, avatar}` — создаёт агента в комнате

---

## LLM и сообщения

### POST `/api/rooms/{roomId}/messages` — общий чат комнаты (рекомендуется)
- Сообщение пользователя в комнату (все агенты видят)
- В режиме `single`: триггер ответа от **каждого** агента (все отвечают)
- В режиме оркестрации (`circular`, `narrator`, `full_context`): сообщение идёт в очередь оркестрации
- Ответы рассылаются в WebSocket `/api/rooms/{roomId}/chat`

### POST `/api/rooms/{roomId}/agents/{agentId}/messages` — личная переписка
- Сообщение **конкретному** агенту (чат 1-на-1)
- Вызывается **YandexGPT** через `YandexAgentClient`
- Ответ сохраняется в БД, возвращается в `agentResponse`
- Сообщение и ответ рассылаются в WebSocket
- **WebSocket должен быть подключён до отправки** — иначе broadcast не доставит сообщения клиенту

---

## Оркестрация

### Pipeline обмена сообщениями

```
User → POST /rooms/{roomId}/messages
     → Сохранить сообщение (agent_id=None)
     → Broadcast в WebSocket
     → enqueue_user_message(room_id, text, sender)
     → UserMessageEvent в очередь оркестрации
     → strategy.handle_user_message
     → tick loop → агенты отвечают
     → ответы в БД + broadcast
```

### Тип комнаты `orchestration_type`
- `single` — пользователь общается с агентами (все отвечают напрямую)
- `circular` — агенты общаются по кругу
- `narrator` — агент-рассказчик
- `full_context` — полный контекст для всех

**Создание:** `POST /api/rooms` с `{"name": "...", "orchestration_type": "circular"}`  
**PATCH /api/rooms/{id}** — только `description` и `speed` (orchestration_type не меняется).

### Ручное управление
- `POST /api/rooms/{roomId}/orchestration/start` — запуск `OrchestrationClient`
- `POST /api/rooms/{roomId}/orchestration/stop` — остановка

### Интеграция чата с оркестрацией
- При первом `POST /messages` в комнате с оркестрацией создаётся `OrchestrationClient`
- При старте загружается **история комнаты из БД** в контекст оркестрации
- `enqueue_user_message(room_id, text, sender)` ставит `UserMessageEvent` в очередь
- Стратегия обрабатывает событие, tick loop генерирует ответы агентов

---

## Сервисы (relationship, memory, emotions)

### Эндпоинты
- `GET /api/rooms/{id}/relationship-model` — граф отношений
- `GET /api/rooms/{id}/emotional-state` — эмоции агентов
- `GET /api/rooms/{id}/context-memory` — сводка диалога

### Обогащение промптов
- LLM и оркестрация получают контекст отношений из `relationship_model`

---

## Тесты

```bash
SQLITE_DB_PATH=:memory: pytest tests/ -v
```

| Файл | Что проверяет |
|------|---------------|
| `tests/test_llm_service.py` | AgentPromptAdapter, fallback без ключей |
| `tests/test_message_endpoint_integration.py` | POST messages → LLM → broadcast |
| `tests/test_orchestration.py` | OrchestrationClient, CircularStrategy |
