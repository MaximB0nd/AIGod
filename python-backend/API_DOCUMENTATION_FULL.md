# AIgod API — полная документация

Единый справочник по API бэкенда AIgod для хакатона «Виртуальный мир: симулятор живых существ». Объединяет все документы: REST API, WebSocket, подключение клиента, оркестрацию и интеграцию.

---

## Оглавление

1. [Обзор и быстрый старт](#1-обзор-и-быстрый-старт)
2. [Подключение и базовые URL](#2-подключение-и-базовые-url)
3. [REST API — полный справочник](#3-rest-api--полный-справочник)
4. [WebSocket](#4-websocket)
5. [Руководство для клиента](#5-руководство-для-клиента)
6. [Архитектура и структура](#6-архитектура-и-структура)
7. [Интеграция и конфигурация](#7-интеграция-и-конфигурация)
8. [Оркестрация агентов](#8-оркестрация-агентов)
9. [Исправления оркестрации](#9-исправления-оркестрации)
10. [Модуль оркестрации (внутренняя документация)](#10-модуль-оркестрации-внутренняя-документация)
11. [Yandex Agent (справочная информация)](#11-yandex-agent-справочная-информация)
12. [Устранение неполадок](#12-устранение-неполадок)

---

# 1. Обзор и быстрый старт

## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env   # заполнить YANDEX_CLOUD_*, API_MESSAGE_LIMIT_PER_DAY
uvicorn app.main:app --reload --port 8000
```

**Важно:** `API_MESSAGE_LIMIT_PER_DAY` в `.env` — лимит вызовов Yandex API в день.

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Чек-лист подключения

- [ ] Сервер запущен (`uvicorn app.main:app`)
- [ ] Переменные `YANDEX_CLOUD_FOLDER` и `YANDEX_CLOUD_API_KEY` заданы в `.env`
- [ ] Клиент подключается по `http://localhost:8000`
- [ ] **WebSocket подключается ДО отправки сообщений** — иначе ответы агентов не придут
- [ ] Все защищённые запросы содержат заголовок `Authorization: Bearer <token>`

## Минимальный flow

```
1. POST /api/auth/login        → токен
2. ws://host/api/rooms/{id}/chat?token=...  → подключить
3. POST /api/rooms/{id}/messages           → отправить сообщение
4. Получить ответы по WebSocket (type: "message")
```

---

# 2. Подключение и базовые URL

| Режим      | REST API                    | WebSocket              |
|------------|----------------------------|------------------------|
| Локально   | `http://localhost:8000`    | `ws://localhost:8000`  |
| Production | `https://your-domain.com`  | `wss://your-domain.com`|

- **Swagger:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Без авторизации

- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/agents`, `GET /api/default-agents`, `GET /api/default-agents/{id}`
- `GET /api/prompts/*`

## С авторизацией (Bearer token)

```
Authorization: Bearer <token>
```

Токен получают из `POST /api/auth/login` (поле `token`).

## WebSocket

Подключение: `ws://localhost:8000/api/rooms/{roomId}/chat?token=JWT`  
Токен передаётся в query-параметре.

---

# 3. REST API — полный справочник

## 3.1 Системные

### GET /
Проверка работы сервера.

**Ответ:**
```json
{
  "message": "AIgod backend",
  "docs": "/docs",
  "api": "/api"
}
```

### GET /api/
Проверка работы API.

**Ответ:**
```json
{
  "message": "AIgod backend работает"
}
```

### GET /api/test-chromadb
Проверка работы ChromaDB (память с векторным поиском). **Без авторизации.**

**Ответ:** `{"chromadb_available": bool, "vector_store_init": bool, "error": str?}`

### GET /api/test-db
Проверка подключения к БД.

**Ответ:**
```json
{
  "status": "база подключена"
}
```

### GET /api/usage
Статистика обращений к Yandex API. **Без авторизации.**

**Ответ:**
```json
{
  "today": "2025-02-18",
  "callCount": 42,
  "limitPerDay": 500,
  "remaining": 458,
  "limitExceeded": false
}
```

---

## 3.2 Авторизация

### POST /api/auth/register
Регистрация пользователя.

**Тело (JSON):**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "username": "optional_username"
}
```

**Ответ (201):**
```json
{
  "id": "1",
  "email": "user@example.com",
  "username": "user",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": ""
}
```

### POST /api/auth/login
Вход в аккаунт.

**Тело (JSON):**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Ответ:**
```json
{
  "id": "1",
  "email": "user@example.com",
  "username": "user",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": ""
}
```

**Ошибки:** 401 — неверный email/пароль, 403 — пользователь неактивен.

### GET /api/auth/me
Текущий пользователь. **Требует Bearer token.**

---

## 3.3 Комнаты

### GET /api/rooms
Список комнат пользователя. **Требует Bearer token.**

### POST /api/rooms
Создать комнату. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "name": "Новая комната",
  "description": "Опционально",
  "orchestration_type": "single"
}
```

| Поле               | По умолчанию | Описание                                                                 |
|--------------------|--------------|---------------------------------------------------------------------------|
| name               | —            | Обязательно                                                              |
| description        | null         | Описание комнаты                                                         |
| orchestration_type | `"single"`   | `single` \| `circular` \| `narrator` \| `full_context`                    |

### GET /api/rooms/{roomId}
Информация о комнате. **Требует Bearer token.**

### PATCH /api/rooms/{roomId}
Изменить комнату (description, speed). **Требует Bearer token.**

### DELETE /api/rooms/{roomId}
Удалить комнату. **Требует Bearer token.**

---

## 3.4 Агенты в комнате

### GET /api/rooms/{roomId}/agents
Все агенты комнаты. **Требует Bearer token.**

### GET /api/rooms/{roomId}/agents/{agentId}
Полная информация по агенту: характер, воспоминания, планы, взаимоотношения. **Требует Bearer token.**

**Важно:** Все поля (keyMemories, plans, relationships) присутствуют всегда — при отсутствии данных это пустые массивы `[]`.

### POST /api/rooms/{roomId}/agents
Создать агента или добавить существующего. **Требует Bearer token.**

**Вариант 1 — создать нового:**
```json
{
  "name": "Мой агент",
  "character": "Описание личности",
  "avatar": "https://..."
}
```

**Вариант 2 — добавить существующего по ID:**
```json
{
  "name": "Копатыч",
  "agentId": 1
}
```

### DELETE /api/rooms/{roomId}/agents/{agentId}
Удалить агента из комнаты. **Требует Bearer token.**

### GET /api/rooms/{roomId}/agents/{agentId}/memories
Воспоминания агента. **Query:** `limit` (1–100, default 20), `offset` (default 0)

### GET /api/rooms/{roomId}/agents/{agentId}/plans
Планы агента. **Требует Bearer token.**

---

## 3.5 Отношения и модель

### PATCH /api/rooms/{roomId}/relationships
Обновить ребро графа. Рассылает `edge_update` в WebSocket графа.

**Тело (JSON):**
```json
{
  "agent1Id": 1,
  "agent2Id": 2,
  "sympathyLevel": 0.7
}
```
`sympathyLevel`: -1.0 .. 1.0

### GET /api/rooms/{roomId}/relationships
Граф отношений комнаты. **Требует Bearer token.**

### GET /api/rooms/{roomId}/relationship-model
Расширенные данные: граф, типы, история, статистика. **Требует Bearer token.**

### GET /api/rooms/{roomId}/emotional-state
Эмоциональное состояние агентов. **Требует Bearer token.**

### GET /api/rooms/{roomId}/context-memory
Контекст/память разговора комнаты. **Query:** `query` (string, опционально)

---

## 3.6 Оркестрация

### POST /api/rooms/{roomId}/orchestration/start
Запустить оркестрацию. Работает только для `orchestration_type != "single"`.

### POST /api/rooms/{roomId}/orchestration/stop
Остановить оркестрацию.

---

## 3.7 События

### POST /api/rooms/{roomId}/events
Создать событие. **Тело:** `{ "description": "...", "type": "user_event", "agentIds": ["1", "2"] }`

### POST /api/rooms/{roomId}/events/broadcast
Событие для всех агентов.  
Если `type` = `"user_message"` или `"chat"`, `description` трактуется как сообщение пользователя — создаётся Message, broadcast, триггер ответов агентов.

---

## 3.8 Сообщения

### POST /api/rooms/{roomId}/messages
Отправить сообщение в общий чат. **Рекомендуемый эндпоинт для multi-agent.**

**Тело (JSON):**
```json
{
  "text": "Привет!",
  "sender": "user"
}
```

Ответы агентов приходят через WebSocket.

### POST /api/rooms/{roomId}/agents/{agentId}/messages
Сообщение конкретному агенту (1-на-1).

### GET /api/rooms/{roomId}/messages
Сообщения комнаты (ленивая загрузка). **Query:** `after_id` (int), `limit` (1–100, default 20)

---

## 3.9 Лента и скорость

### GET /api/rooms/{roomId}/feed
Лента (сообщения + события). **Query:** `limit` (1–100, default 20)

### PATCH /api/rooms/{roomId}/speed
Изменить скорость симуляции. **Тело:** `{ "speed": 2.0 }` (0.1–10.0)

---

## 3.10 Промпты

### GET /api/prompts/system
Системные промпты. **Без авторизации.**

### GET /api/prompts/templates
Список шаблонов. **Без авторизации.**

### GET /api/prompts/templates/{name}
Шаблон по имени. **Без авторизации.**

### POST /api/prompts/build
Собрать промпт из шаблона. **Без авторизации.**

---

## 3.11 Шаблоны агентов (default-agents)

### GET /api/default-agents
Список шаблонов для создания агента. **Без авторизации.**

### GET /api/default-agents/{id}
Шаблон по id. **Без авторизации.**

---

## 3.12 Каталог агентов

### GET /api/agents
Агенты в БД (созданные пользователями). **Без авторизации.**

---

## 3.13 Сводная таблица эндпоинтов

| Метод  | Путь                                          | Auth  |
|--------|------------------------------------------------|-------|
| GET    | /                                             | —     |
| GET    | /api/                                         | —     |
| GET    | /api/test-db                                 | —     |
| POST   | /api/auth/register                            | —     |
| POST   | /api/auth/login                               | —     |
| GET    | /api/auth/me                                  | Bearer|
| GET    | /api/rooms                                    | Bearer|
| POST   | /api/rooms                                    | Bearer|
| GET    | /api/rooms/{roomId}                           | Bearer|
| PATCH  | /api/rooms/{roomId}                           | Bearer|
| DELETE | /api/rooms/{roomId}                           | Bearer|
| GET    | /api/rooms/{roomId}/agents                    | Bearer|
| GET    | /api/rooms/{roomId}/agents/{agentId}          | Bearer|
| POST   | /api/rooms/{roomId}/agents                    | Bearer|
| DELETE | /api/rooms/{roomId}/agents/{agentId}         | Bearer|
| GET    | /api/rooms/{roomId}/agents/{agentId}/memories | Bearer|
| GET    | /api/rooms/{roomId}/agents/{agentId}/plans   | Bearer|
| PATCH  | /api/rooms/{roomId}/relationships            | Bearer|
| GET    | /api/rooms/{roomId}/relationships            | Bearer|
| GET    | /api/rooms/{roomId}/relationship-model       | Bearer|
| GET    | /api/rooms/{roomId}/emotional-state           | Bearer|
| GET    | /api/rooms/{roomId}/context-memory            | Bearer|
| POST   | /api/rooms/{roomId}/orchestration/start      | Bearer|
| POST   | /api/rooms/{roomId}/orchestration/stop       | Bearer|
| POST   | /api/rooms/{roomId}/events                    | Bearer|
| POST   | /api/rooms/{roomId}/events/broadcast          | Bearer|
| GET    | /api/rooms/{roomId}/messages                  | Bearer|
| POST   | /api/rooms/{roomId}/messages                  | Bearer|
| POST   | /api/rooms/{roomId}/agents/{agentId}/messages | Bearer|
| GET    | /api/rooms/{roomId}/feed                      | Bearer|
| PATCH  | /api/rooms/{roomId}/speed                     | Bearer|
| GET    | /api/default-agents                           | —     |
| GET    | /api/default-agents/{id}                      | —     |
| GET    | /api/agents                                   | —     |
| GET    | /api/prompts/system                            | —     |
| GET    | /api/prompts/templates                        | —     |
| GET    | /api/prompts/templates/{name}                 | —     |
| POST   | /api/prompts/build                            | —     |
| WS     | /api/rooms/{roomId}/chat?token=               | JWT   |
| WS     | /api/rooms/{roomId}/graph?token=              | JWT   |

---

# 4. WebSocket

## 4.1 Чат комнаты

**Endpoint:** `WS /api/rooms/{roomId}/chat`

```
ws://localhost:8000/api/rooms/1/chat?token=YOUR_JWT_TOKEN
```

**Коды закрытия:**
| Код  | Значение                                |
|------|-----------------------------------------|
| 4001 | Unauthorized (нет или неверный token)   |
| 4003 | Forbidden (нет доступа к комнате)       |

**Важно:** Подключать WebSocket **до** отправки сообщений, иначе broadcast не дойдёт.

### Входящие от сервера

Все сообщения: `{"type": string, "payload": object}`.

| type      | Описание                    |
|-----------|-----------------------------|
| connected | Успешное подключение       |
| message   | Новое сообщение в чате      |
| event     | Событие в комнате           |
| pong      | Ответ на ping               |
| error     | Ошибка сервера              |

**connected:**
```json
{
  "type": "connected",
  "payload": {
    "roomId": "1",
    "message": "Подключено к чату комнаты"
  }
}
```

**message:**
```json
{
  "type": "message",
  "payload": {
    "id": "42",
    "text": "Текст сообщения",
    "sender": "Маркетолог",
    "agentId": "1",
    "timestamp": "2025-02-16T14:30:00"
  }
}
```

**Значения `sender` (режим circular):**
- Имя агента комнаты
- `"🎭 Рассказчик Нарратор"` — нарративные фрагменты
- `"📊 Сводка Суммаризатор"` — структурированная сводка раунда
- `"Система"` — финальный синтез или «=== Раунд X завершён ===»
- `"user"` — сообщение пользователя

### Исходящие от клиента

**Ping (раз в 20–30 сек):**
```json
{"type": "ping"}
```

---

## 4.2 Граф отношений

**Endpoint:** `WS /api/rooms/{roomId}/graph`

```
ws://localhost:8000/api/rooms/1/graph?token=YOUR_JWT_TOKEN
```

**Входящие:** `connected`, `edge_update`, `pong`, `error`

**edge_update:**
```json
{
  "type": "edge_update",
  "payload": {
    "roomId": "1",
    "from": "1",
    "to": "2",
    "sympathyLevel": 0.7
  }
}
```

---

## 4.3 Примеры кода (JavaScript)

```javascript
const token = "eyJ...";
const roomId = 1;
const ws = new WebSocket(`ws://localhost:8000/api/rooms/${roomId}/chat?token=${token}`);

ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === "connected") {
    console.log("Подключено:", data.payload.message);
  }
  if (data.type === "message") {
    const { id, text, sender, agentId } = data.payload;
    console.log(`${sender}: ${text}`);
  }
};

ws.onopen = () => {
  setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 25000);
};
```

---

# 5. Руководство для клиента

## 5.1 Типичный сценарий

1. **Логин:** `POST /api/auth/login` → сохранить `token`
2. **Подключить WebSocket** к чату **до** отправки сообщений
3. **Комната:** `POST /api/rooms` с `orchestration_type`
4. **Агенты:** `POST /api/rooms/{id}/agents` или через default-agents
5. **Сообщение:** `POST /api/rooms/{id}/messages` → ответы агентов придут по WebSocket
6. **История:** `GET /api/rooms/{id}/messages` или `/feed`

## 5.2 Переменные окружения (сервер)

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `YANDEX_CLOUD_FOLDER` | Да* | ID папки в Yandex Cloud |
| `YANDEX_CLOUD_API_KEY` | Да* | API-ключ Yandex GPT |
| `SECRET_KEY` | Нет | JWT secret |
| `SQLITE_DB_PATH` | Нет | Путь к БД (по умолчанию `agents.db`) |
| `CHROMA_PERSIST_DIR` | Нет | Путь к ChromaDB для памяти |

\* Без Yandex ключей оркестрация не запустится — fallback в режим single.

## 5.3 Пример полной интеграции (JavaScript)

```javascript
const API = "http://localhost:8000";
const WS = "ws://localhost:8000";

async function login(email, password) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!data.token) throw new Error("Login failed");
  return data.token;
}

async function createRoom(token, name, orchestrationType = "circular") {
  const res = await fetch(`${API}/api/rooms`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({
      name,
      orchestration_type: orchestrationType,
      description: "",
    }),
  });
  return res.json();
}

async function addAgent(token, roomId, name, character) {
  const res = await fetch(`${API}/api/rooms/${roomId}/agents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ name, character }),
  });
  return res.json();
}

function connectChat(roomId, token, onMessage) {
  const ws = new WebSocket(`${WS}/api/rooms/${roomId}/chat?token=${token}`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "message") onMessage(data.payload);
  };
  ws.onopen = () => {
    setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 25000);
  };
  return ws;
}

async function sendMessage(token, roomId, text) {
  const res = await fetch(`${API}/api/rooms/${roomId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ text, sender: "user" }),
  });
  return res.json();
}
```

---

# 6. Архитектура и структура

## 6.1 Общая архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AIgod Backend                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  REST API (/api)              │  WebSocket (/api/rooms/{id}/chat|graph)  │
├─────────────────────────────────────────────────────────────────────────┤
│  • Auth (register, login)      │  • Чат: connected, message, event       │
│  • Rooms CRUD                  │  • Граф: connected, edge_update         │
│  • Room Agents, Messages       │                                          │
│  • Prompts, Default Agents     │                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Pipeline Executor (type≠single): RETRIEVE_MEMORY → PLAN → DISCUSS →     │
│  SYNTHESIZE → STORE_MEMORY → UPDATE_GRAPH → DONE                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Основные сущности

| Сущность     | Описание                                                    |
|--------------|-------------------------------------------------------------|
| **User**     | Пользователь (email, password). Авторизация JWT.           |
| **Room**     | Комната с агентами, `orchestration_type`, `description`.    |
| **Agent**    | Агент в комнате: `name`, `personality`, `avatar`.           |
| **Message**  | Сообщение в комнате: `text`, `sender`, `agentId` (или null).|
| **Relationship** | Связь между агентами (sympathy).                          |

## 6.3 Режимы оркестрации (`orchestration_type`)

| Режим           | Поведение                                                     |
|-----------------|---------------------------------------------------------------|
| `single`       | Каждый агент отвечает отдельно (по умолчанию).               |
| `circular`     | Агенты общаются по кругу, до 50 раундов. Рассказчик (🎭) и Суммаризатор (📊). |
| `narrator`     | Один агент-рассказчик ведёт историю, остальные — персонажи.   |
| `full_context` | Обсуждение с суммаризацией раундов.                           |

## 6.4 Pipeline Executor

Каждый запрос при `orchestration_type != single` проходит этапы:

| Этап | Описание |
|------|----------|
| RETRIEVE_MEMORY | Загрузка релевантного контекста из ChromaDB |
| PLAN | План (фокус на запросе пользователя) |
| DISCUSS | Обсуждение агентов (Circular/Narrator/FullContext) |
| SYNTHESIZE | SolutionSynthesizer — финальный ответ пользователю |
| STORE_MEMORY | Сохранение в память |
| FACT_EXTRACTION | Извлечение структурированных фактов |
| UPDATE_GRAPH | Обновление графа отношений |
| DONE | Завершение |

---

# 7. Интеграция и конфигурация

## 7.1 Переменные окружения (`.env`)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `YANDEX_CLOUD_FOLDER` | folder_id в Yandex Cloud | — |
| `YANDEX_CLOUD_API_KEY` | API key | — |
| `API_MESSAGE_LIMIT_PER_DAY` | Лимит вызовов Yandex API в день (0 = без ограничений) | `0` |
| `SQLITE_DB_PATH` | Путь к SQLite БД | `aigod.db` |
| `SECRET_KEY` | JWT секрет | (встроенный) |
| `LOG_LEVEL` | Уровень логов: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

## 7.2 Архитектура чата

- **`POST /api/rooms/{roomId}/messages`** — сообщение в общий чат комнаты.
  - Режим `single`: триггер ответа от каждого агента.
  - Режим оркестрации: `enqueue_user_message` → `UserMessageEvent` → strategy → ответы.
- **`POST /api/rooms/{roomId}/agents/{agentId}/messages`** — личная переписка с конкретным агентом.

## 7.3 Таблица `agents` и `default_agents`

- **agents** — созданные пользователями агенты. Изначально пуста.
- **default_agents** — шаблоны (Копатыч, Гермиона, Нарратор, Суммаризатор и т.д.). В режиме `circular` Рассказчик и Суммаризатор добавляются автоматически.

## 7.4 CORS

По умолчанию FastAPI разрешает запросы с любого origin. Для production настройте CORS в `app/main.py`.

---

# 8. Оркестрация агентов

## 8.1 Pipeline обмена сообщениями

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

## 8.2 Тип комнаты `orchestration_type`

- `single` — пользователь общается с агентами (все отвечают напрямую)
- `circular` — агенты по кругу. Рассказчик (🎭) и Суммаризатор (📊). До 50 раундов.
- `narrator` — агент-рассказчик
- `full_context` — полный контекст для всех

## 8.3 Ручное управление

- `POST /api/rooms/{roomId}/orchestration/start` — запуск OrchestrationClient
- `POST /api/rooms/{roomId}/orchestration/stop` — остановка

---

# 9. Исправления оркестрации

## 9.1 Что исправлено

### Агенты игнорировали пользователя
- Запрос пользователя сохраняется в `ConversationContext` и передаётся в каждый промпт.
- Блок **«ЗАПРОС ПОЛЬЗОВАТЕЛЯ (ГЛАВНЫЙ ФОКУС)»** в промптах.
- Circular: до **50 раундов** (ранее 5).

### Память комнаты (ChromaDB)
- При наличии `CHROMA_PERSIST_DIR` используется векторное хранилище.
- Коллекции: `room_memory_{room_id}`.
- Промпт обогащается релевантными воспоминаниями.

### Граф отношений
- `HeuristicRelationshipAnalyzer` по ключевым словам («согласен», «не согласен» и т.п.).
- Граф обновляется при каждом сообщении агента.

## 9.2 Изменения для клиента

- Эндпоинты и форматы ответов **не изменились**.
- WebSocket: поле `sender` может содержать `🎭 Рассказчик Нарратор`, `📊 Сводка Суммаризатор`, `Система`.

## 9.3 Логи для отладки

| Лог | Значение |
|-----|----------|
| `orchestration get_or_start room_id=X создаём клиент type=Y` | Создан оркестратор |
| `orchestration_client enqueue_user_message room_id=X` | Сообщение в очереди |
| `orchestration on_message room_id=X type=agent sender=Y` | Сообщение сохранено и разослано |
| `orchestration memory stored room_id=X` | Диалог сохранён в память |
| `orchestration graph updated room_id=X sender=Y` | Граф обновлён |
| `create_orchestration_client room_id=X type=Y strategy=Z` | Выбрана стратегия |

---

# 10. Модуль оркестрации (внутренняя документация)

## 10.1 Структура модуля

```
agents_orchestration/
├── __init__.py
├── events.py                    # UserMessageEvent
├── message_type.py              # Типы сообщений (Enum)
├── message.py                   # Модель сообщения
├── context.py                   # Контекст разговора
├── base_strategy.py             # Базовый класс стратегии
├── orchestration_client.py      # Основной клиент
├── strategies/
│   ├── circular.py                        # Циркулярная стратегия
│   ├── circular_with_narrator_summarizer.py # + Рассказчик + Суммаризатор
│   ├── narrator.py                        # Стратегия с рассказчиком
│   └── full_context.py                    # Полный контекст
```

## 10.2 Типы сообщений (MessageType)

- `USER` — сообщение от пользователя
- `AGENT` — сообщение от агента
- `SYSTEM` — системное сообщение
- `NARRATOR` — сообщение от рассказчика
- `SUMMARIZED` — сводка обсуждения

## 10.3 Стратегии

| Стратегия | Когда использовать |
|-----------|-------------------|
| Circular | Простой диалог, мозговой штурм |
| Narrator | Создание историй, ролевые игры |
| FullContext | Сложные обсуждения, требующие анализа |

## 10.4 OrchestrationClient API

```python
client = OrchestrationClient(agents, chat_service)
client.set_strategy(strategy)
client.on_message(callback)
await client.start(max_ticks=10)
await client.enqueue_user_message(room_id, text, sender)
await client.stop()
```

---

# 11. Yandex Agent (справочная информация)

Готовая система для интеграции AI-агентов на базе YandexGPT в FastAPI.

## Быстрый старт

```bash
pip install fastapi uvicorn python-dotenv yandex-ai-studio-sdk
```

## .env

```
YANDEX_CLOUD_FOLDER=your_folder_id
YANDEX_CLOUD_API_KEY=your_api_key
```

## Основные эндпоинты (упрощённая версия)

- `GET /agents` — список агентов
- `GET /agents/{name}` — информация об агенте
- `POST /agents/create` — создать агента
- `POST /chat` — отправить сообщение агенту

**Формат chat:**
```json
{
  "agent_name": "копатич",
  "session_id": "user_123",
  "message": "Привет!"
}
```

---

# 12. Устранение неполадок

## Агенты не отвечают

- Проверьте, что WebSocket **подключён до** отправки сообщения
- Убедитесь, что в комнате есть агенты
- Для orchestration: проверьте `YANDEX_CLOUD_FOLDER` и `YANDEX_CLOUD_API_KEY`

## 401 Unauthorized

- Токен не передан или истёк
- Добавьте `Authorization: Bearer <token>`

## 403 Forbidden (WebSocket)

- Пользователь не имеет доступа к комнате

## Оркестрация не запускается

- Проверьте `orchestration_type` комнаты (не `single`)
- В логах: `create_pipeline_components YandexAgentClient fail` — нет Yandex ключей

## Сообщения приходят с задержкой

- Pipeline выполняет несколько этапов (memory, discuss, synthesize). Это нормально.
- В режиме circular — до 50 раундов обсуждения.

## Чат пустой (сообщения в БД, но не отображаются)

1. **WebSocket подключён?** — Подключение должно быть до отправки.
2. **Правильный roomId?** — URL должен совпадать с комнатой.
3. **Логи сервера** — при broadcast с 0 подключений: `broadcast room_id=X — 0 подключений`.
4. **Начальная загрузка** — вызовите `GET /api/rooms/{roomId}/messages` при открытии чата.

## Тесты

```bash
SQLITE_DB_PATH=:memory: pytest tests/ -v
```

---

*Документ объединяет: API_DOCS.md, CLIENT_DOCUMENTATION.md, CLIENT_GUIDE.md, CONNECTION.md, INTEGRATION.md, ORCHESTRATION_FIXES.md, README.md, WEBSOCKET_CLIENT.md, yandex_agent_documentation.md, agents_orchestration_documentation.md*
