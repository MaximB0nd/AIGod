# Документация API для клиента (AIgod)

Единый справочник по API, структуре системы и последним изменениям для разработчиков фронтенда и интеграторов.

---

## 1. Общая структура

### 1.1 Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AIgod Backend                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  REST API (/api)              │  WebSocket (/api/rooms/{id}/chat|graph)  │
├─────────────────────────────────────────────────────────────────────────┤
│  • Auth (register, login)      │  • Чат: connected, message, event       │
│  • Rooms CRUD                  │  • Граф: connected, edge_update         │
│  • Room Agents, Messages       │                                          │
│  • Prompts, Default Agents    │                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Pipeline Executor (type≠single): RETRIEVE_MEMORY → PLAN → DISCUSS →     │
│  SYNTHESIZE → STORE_MEMORY → UPDATE_GRAPH → DONE (обязательные этапы)     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Основные сущности

| Сущность     | Описание                                                    |
|--------------|-------------------------------------------------------------|
| **User**     | Пользователь (email, password). Авторизация JWT.           |
| **Room**     | Комната с агентами, `orchestration_type`, `description`.    |
| **Agent**    | Агент в комнате: `name`, `personality`, `avatar`.           |
| **Message**  | Сообщение в комнате: `text`, `sender`, `agentId` (или null).|
| **Relationship** | Связь между агентами (sympathy).                          |

### 1.3 Режимы оркестрации (`orchestration_type`)

| Режим           | Поведение                                                     |
|-----------------|---------------------------------------------------------------|
| `single`       | Каждый агент отвечает отдельно (по умолчанию).               |
| `circular`     | Агенты общаются по кругу, до 5 раундов, фокус на запросе.    |
| `narrator`     | Один агент-рассказчик ведёт историю, остальные — персонажи.   |
| `full_context` | Обсуждение с суммаризацией раундов.                           |

---

## 2. Базовые URL

| Режим      | REST API                    | WebSocket              |
|------------|----------------------------|------------------------|
| Локально   | `http://localhost:8000`    | `ws://localhost:8000`  |
| Production | `https://your-domain.com`  | `wss://your-domain.com`|

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3. REST API

### 3.1 Авторизация

Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <token>
```

| Метод | Путь                | Описание     |
|-------|---------------------|--------------|
| POST  | /api/auth/register  | Регистрация  |
| POST  | /api/auth/login     | Логин        |
| GET   | /api/auth/me        | Текущий юзер |

### 3.2 Комнаты

| Метод | Путь          | Описание              |
|-------|---------------|-----------------------|
| GET   | /api/rooms    | Список комнат         |
| POST  | /api/rooms    | Создать комнату       |
| GET   | /api/rooms/{id} | Получить комнату    |
| PATCH | /api/rooms/{id} | Обновить комнату    |
| DELETE| /api/rooms/{id} | Удалить комнату     |

**Создание комнаты:**
```json
POST /api/rooms
{
  "name": "Моя комната",
  "orchestration_type": "circular",
  "description": "Обсуждение тем"
}
```

### 3.3 Агенты в комнате

| Метод | Путь                          | Описание                    |
|-------|-------------------------------|-----------------------------|
| GET   | /api/rooms/{id}/agents        | Список агентов             |
| GET   | /api/rooms/{id}/agents/{aid}  | Агент по ID                 |
| POST  | /api/rooms/{id}/agents        | Добавить агента            |
| DELETE| /api/rooms/{id}/agents/{aid}  | Удалить агента             |

### 3.4 Сообщения и лента

| Метод | Путь                              | Описание                    |
|-------|-----------------------------------|-----------------------------|
| POST  | /api/rooms/{id}/messages         | Сообщение в общий чат      |
| GET   | /api/rooms/{id}/messages         | История сообщений         |
| GET   | /api/rooms/{id}/feed             | Лента (сообщения + события)|
| POST  | /api/rooms/{id}/agents/{aid}/messages | Сообщение конкретному агенту |

**Отправка сообщения в общий чат (оркестрация):**
```json
POST /api/rooms/{roomId}/messages
{
  "text": "Привет!",
  "sender": "user"
}
```

### 3.5 Отношения и модель

| Метод | Путь                                  | Описание                     |
|-------|---------------------------------------|------------------------------|
| GET   | /api/rooms/{id}/relationships         | Отношения между агентами     |
| PATCH | /api/rooms/{id}/relationships         | Обновить отношение           |
| GET   | /api/rooms/{id}/relationship-model    | Граф + статистика            |
| GET   | /api/rooms/{id}/emotional-state       | Эмоциональное состояние      |
| GET   | /api/rooms/{id}/context-memory        | Сводка по памяти            |

### 3.6 Оркестрация (ручное управление)

| Метод | Путь                                | Описание              |
|-------|-------------------------------------|------------------------|
| POST  | /api/rooms/{id}/orchestration/start | Запустить оркестрацию |
| POST  | /api/rooms/{id}/orchestration/stop  | Остановить оркестрацию|

### 3.7 Остальное

| Метод | Путь                     | Описание                 |
|-------|--------------------------|--------------------------|
| GET   | /api/default-agents      | Шаблоны агентов          |
| GET   | /api/default-agents/{id} | Шаблон по ID             |
| GET   | /api/prompts/system      | Системные промпты        |
| GET   | /api/prompts/templates   | Шаблоны промптов         |
| POST  | /api/prompts/build       | Сборка промпта           |
| GET   | /api/agents              | Каталог агентов          |
| POST  | /api/rooms/{id}/events    | Создать событие          |
| POST  | /api/rooms/{id}/events/broadcast | Broadcast события |

---

## 4. WebSocket

### 4.1 Чат

```
ws://localhost:8000/api/rooms/{roomId}/chat?token={JWT}
```

**Входящие:** `connected`, `message`, `event`, `pong`, `error`

**Ответ агентов** приходят через `message` с полями: `id`, `text`, `sender`, `agentId`, `timestamp`.

**Клиент** отправляет `{"type": "ping"}` раз в 20–30 сек.

### 4.2 Граф отношений

```
ws://localhost:8000/api/rooms/{roomId}/graph?token={JWT}
```

**Входящие:** `connected`, `edge_update`, `pong`, `error`

Граф обновляется при каждом сообщении агента (по ключевым словам: «согласен», «не согласен» и т.п.).

---

## 5. Типичный сценарий для клиента

1. **Логин:** `POST /api/auth/login` → сохранить `token`
2. **Подключить WebSocket** к чату **до** отправки сообщений
3. **Комната:** `POST /api/rooms` с `orchestration_type`
4. **Агенты:** `POST /api/rooms/{id}/agents` или через default-agents
5. **Сообщение:** `POST /api/rooms/{id}/messages` → ответы агентов придут по WebSocket
6. **История:** `GET /api/rooms/{id}/messages` или `/feed`

---

## 6. Pipeline Executor (единый движок)

Каждый запрос пользователя при `orchestration_type != single` **обязательно** проходит этапы:

| Этап | Описание |
|------|----------|
| RETRIEVE_MEMORY | Загрузка релевантного контекста из ChromaDB |
| PLAN | План (фокус на запросе пользователя) |
| DISCUSS | Обсуждение агентов (стратегия Circular/Narrator/FullContext) |
| SYNTHESIZE | **SolutionSynthesizer** — FINAL DECISION MAKER, принять решение и ответить пользователю |
| STORE_MEMORY | Сохранение в память |
| FACT_EXTRACTION | Извлечение структурированных фактов (триплетов) из диалога |
| UPDATE_GRAPH | Обновление графа отношений (из facts + heuristic) |
| DONE | Завершение |

Память, граф и суммаризация — **обязательные** шаги, а не опциональные сервисы.

---

## 7. Изменения (актуальная версия)

### 7.1 Агенты больше не теряют фокус на запросе

- Запрос пользователя явно передаётся в промпт каждого агента.
- Добавлен блок **«ЗАПРОС ПОЛЬЗОВАТЕЛЯ (ГЛАВНЫЙ ФОКУС)»** в промптах.
- Circular-режим останавливается после **5 раундов** (нет бесконечного цикла).

### 7.2 Память комнаты (ChromaDB)

- При наличии ChromaDB (`CHROMA_PERSIST_DIR`) используется векторное хранилище.
- Перед ответом агента промпт обогащается релевантными воспоминаниями.
- Каждый диалог (запрос + ответ) сохраняется в память.

### 7.3 Граф отношений обновляется

- Граф связей между агентами обновляется по каждому сообщению.
- Используется эвристика по ключевым словам без LLM.

### 7.4 Стратегии оркестрации различаются

- **Circular:** агенты по кругу, фокус на запросе, до 5 раундов.
- **Narrator:** рассказчик + персонажи.
- **FullContext:** обсуждение с суммаризацией.

### 7.5 Обратная совместимость

- Эндпоинты и форматы ответов **не изменились**.
- WebSocket-события и структура сообщений прежние.
- Клиенту не требуется менять код, поведение агентов улучшено.

---

## 8. Настройки (для интеграторов)

| Параметр           | Где         | Описание                                      |
|--------------------|-------------|-----------------------------------------------|
| orchestration_type | Создание room | `single`, `circular`, `narrator`, `full_context` |
| CHROMA_PERSIST_DIR | env сервера | Путь к ChromaDB (по умолчанию `./chroma_db`)  |
| max_rounds         | Код (Circular) | Число раундов до остановки (по умолчанию 5)  |

---

## 9. Логи (для отладки)

| Лог | Значение |
|-----|----------|
| `orchestration get_or_start room_id=X создаём клиент type=Y` | Создан оркестратор |
| `orchestration_client enqueue_user_message room_id=X` | Сообщение в очереди |
| `orchestration on_message room_id=X type=agent sender=Y` | Сообщение сохранено и разослано |
| `orchestration memory stored room_id=X` | Диалог сохранён в память |
| `orchestration graph updated room_id=X sender=Y` | Граф обновлён |
| `create_orchestration_client room_id=X type=Y strategy=Z` | Выбрана стратегия |
| `orchestration_client stop room_id=X` | Оркестрация остановлена |

---

## 10. Связанные документы

- **CLIENT_GUIDE.md** — полное руководство для клиента (подключение, примеры, troubleshooting).
- **CONNECTION.md** — краткое подключение, CORS.
- **ORCHESTRATION_FIXES.md** — детали исправлений оркестрации.
- **WEBSOCKET_CLIENT.md** — детали WebSocket.
