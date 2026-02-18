# AIgod API — полная документация (v1.0.0)

Актуальная версия: все REST-эндпоинты и WebSocket.

---

## Подключение

| Параметр       | Значение                        |
|----------------|----------------------------------|
| **Базовый URL**| `http://localhost:8000`         |
| **Swagger UI** | `http://localhost:8000/docs`    |
| **ReDoc**      | `http://localhost:8000/redoc`   |

### Без авторизации
- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/agents`, `GET /api/default-agents`, `GET /api/default-agents/{id}`
- `GET /api/prompts/*`

### С авторизацией (Bearer token)
```
Authorization: Bearer <token>
```
Токен получают из `POST /api/auth/login` (поле `token`).

### WebSocket
Подключение: `ws://localhost:8000/api/rooms/{roomId}/chat?token=JWT`  
Токен передаётся в query-параметре.

---

## 1. Системные

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

---

### GET /api/
Проверка работы API.

**Ответ:**
```json
{
  "message": "AIgod backend работает"
}
```

---

### GET /api/test-chromadb
Проверка работы ChromaDB (память с векторным поиском). **Без авторизации.**

**Ответ:** `{"chromadb_available": bool, "vector_store_init": bool, "error": str?}`  
При `error` и `np.float_` — подсказка: обновить chromadb или понизить NumPy.

---

### GET /api/test-db
Проверка подключения к БД.

**Ответ:**
```json
{
  "status": "база подключена"
}
```

---

## 2. Авторизация

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

| Поле     | Тип    | Обязательно | Описание                              |
|----------|--------|-------------|---------------------------------------|
| email    | string | да          | Валидный email                        |
| password | string | да          | Минимум 8 символов                    |
| username | string | нет         | По умолчанию — часть до @ из email    |

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

---

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

---

### GET /api/auth/me
Текущий пользователь. **Требует Bearer token.**

**Ответ:**
```json
{
  "id": "1",
  "email": "user@example.com",
  "username": "user",
  "token": "",
  "refreshToken": ""
}
```
`token` и `refreshToken` пустые — клиент хранит токен из login.

---

## 3. Комнаты

### GET /api/rooms
Список комнат пользователя. **Требует Bearer token.**

**Ответ:**
```json
{
  "rooms": [
    {
      "id": "1",
      "name": "Моя комната",
      "description": "Описание",
      "speed": 1.0,
      "orchestration_type": "circular",
      "createdAt": "2025-02-16T12:00:00",
      "updatedAt": null,
      "agentCount": 3
    }
  ]
}
```

---

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

| Поле               | Тип    | По умолчанию | Описание                                                                 |
|--------------------|--------|--------------|---------------------------------------------------------------------------|
| name               | string | —            | Обязательно                                                              |
| description        | string | null         | Описание комнаты                                                         |
| orchestration_type | string | `"single"`   | `single` \| `circular` \| `narrator` \| `full_context`                    |

**narrator:** При создании комнаты автоматически добавляется агент «Рассказчик» (видим пользователю). Его нельзя удалить. **circular:** агенты по кругу + ghost-Суммаризатор. **full_context:** обсуждение с суммаризацией.

**Ответ (201):**
```json
{
  "id": "1",
  "name": "Новая комната",
  "description": "Опционально",
  "speed": 1.0,
  "orchestration_type": "single",
  "createdAt": "2025-02-16T12:00:00",
  "updatedAt": null,
  "agentCount": null
}
```

---

### GET /api/rooms/{roomId}
Информация о комнате. **Требует Bearer token.**

**Ответ:** объект Room (как выше).

**Ошибки:** 404 — комната не найдена или нет доступа.

---

### PATCH /api/rooms/{roomId}
Изменить комнату. **Требует Bearer token.**

**Тело (JSON):** оба поля опциональны
```json
{
  "description": "Новое описание",
  "speed": 2.0
}
```
`speed`: 0.1–10.0

**Ответ:** объект Room.

---

### DELETE /api/rooms/{roomId}
Удалить комнату. **Требует Bearer token.**

Удаляются сообщения, события, связи, останавливается оркестрация.

**Ответ:** `204 No Content`

---

## 4. Агенты в комнате

### GET /api/rooms/{roomId}/agents
Все агенты комнаты. **Требует Bearer token.**

**Ответ:**
```json
{
  "agents": [
    {
      "id": "1",
      "name": "Копатыч",
      "avatar": "https://...",
      "mood": {
        "mood": "happy",
        "level": 0.8,
        "icon": "😊",
        "color": "#4ade80"
      }
    }
  ]
}
```

---

### GET /api/rooms/{roomId}/agents/{agentId}
Полная информация по агенту: характер, воспоминания, планы, взаимоотношения. **Требует Bearer token.**

**Ответ:**
```json
{
  "id": "1",
  "name": "Копатыч",
  "avatar": "https://...",
  "mood": { "mood": "happy", "level": 0.8, "icon": "😊", "color": "#4ade80" },
  "character": "Описание личности...",
  "keyMemories": [
    {
      "id": "1",
      "content": "Текст воспоминания",
      "timestamp": "2025-02-16T12:00:00",
      "importance": 0.9
    }
  ],
  "plans": [
    {
      "id": "1",
      "description": "Сделать задание",
      "status": "in_progress"
    }
  ],
  "relationships": [
    {
      "agentId": "2",
      "agentName": "Билл",
      "sympathyLevel": 0.7
    }
  ]
}
```
- `keyMemories` — ключевые воспоминания агента (всегда массив).
- `plans` — активные планы. `status`: `pending` \| `in_progress` \| `done`
- `relationships` — связи с другими агентами комнаты: agentId, agentName, sympathyLevel (-1.0 .. 1.0).

**Важно для фронтенда:** Все три поля (keyMemories, plans, relationships) присутствуют в ответе всегда — при отсутствии данных это пустые массивы `[]`.

**Ошибки:** 404 — агент не найден в комнате.

---

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

| Поле      | Тип   | Обязательно | Описание                                     |
|-----------|-------|-------------|----------------------------------------------|
| name      | string| да          | Имя агента                                   |
| character | string| нет*        | Личность (*обязательно при создании нового)  |
| avatar    | string| нет         | URL аватара                                  |
| agentId   | int   | нет         | ID существующего агента для добавления       |

**Ответ (201):** AgentSummaryOut (id, name, avatar, mood).

**Ошибки:** 400 — дубликат имени или неверные данные.

---

### DELETE /api/rooms/{roomId}/agents/{agentId}
Удалить агента из комнаты. **Требует Bearer token.**

**Ответ:** `204 No Content`

---

### GET /api/rooms/{roomId}/agents/{agentId}/memories
Воспоминания агента. **Требует Bearer token.**

**Query:** `limit` (1–100, default 20), `offset` (default 0)

**Ответ:**
```json
{
  "memories": [
    {
      "id": "1",
      "content": "Текст",
      "timestamp": "2025-02-16T12:00:00",
      "importance": 0.7
    }
  ],
  "total": 42
}
```

---

### GET /api/rooms/{roomId}/agents/{agentId}/plans
Планы агента. **Требует Bearer token.**

**Ответ:**
```json
{
  "plans": [
    {
      "id": "1",
      "description": "Описание",
      "status": "pending"
    }
  ]
}
```

---

## 5. Отношения и модель

### PATCH /api/rooms/{roomId}/relationships
Обновить ребро графа. Рассылает `edge_update` в WebSocket графа. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "agent1Id": 1,
  "agent2Id": 2,
  "sympathyLevel": 0.7
}
```
`sympathyLevel`: -1.0 .. 1.0. Оба агента должны быть в комнате.

**Ответ:**
```json
{
  "from": "1",
  "to": "2",
  "sympathyLevel": 0.7
}
```

**Ошибки:** 400 — одинаковые агенты или не в комнате.

---

### GET /api/rooms/{roomId}/relationships
Граф отношений комнаты. **Требует Bearer token.**

**Ответ:**
```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Копатыч",
      "avatar": null,
      "mood": { "mood": "happy", "level": 0.8, "color": "#4ade80" }
    }
  ],
  "edges": [
    {
      "from": "1",
      "to": "2",
      "agentName": "Билл",
      "sympathyLevel": 0.7
    }
  ]
}
```

---

### GET /api/rooms/{roomId}/relationship-model
Расширенные данные (relationship-model): граф, типы, история, статистика. **Требует Bearer token.**

**Ответ:**
```json
{
  "graph": { "nodes": [...], "edges": [...] },
  "history": [...],
  "stats": { ... },
  "agent_ids": { "Копатыч": "1", "Билл": "2" }
}
```

---

### GET /api/rooms/{roomId}/emotional-state
Эмоциональное состояние агентов. **Требует Bearer token.**

**Ответ:**
```json
{
  "agent_ids": { "Копатыч": "1", "Билл": "2" },
  "states": {
    "Копатыч": { "entity": "Копатыч", "current_state": {...}, "profile": null, "emotional_intelligence": 0.85 },
    "Билл": { ... }
  }
}
```
При недоступности: `{"agents": {}, "message": "Emotional service unavailable"}`.

---

### GET /api/rooms/{roomId}/context-memory
Контекст/память разговора комнаты. **Требует Bearer token.**

**Query:** `query` (string, опционально) — поиск по контексту.

**Ответ:**
```json
{
  "summary": "Краткая сводка диалога...",
  "stats": { "memory_stats": { ... } }
}
```
При недоступности: `{"context": "", "message": "Memory service unavailable"}`.

---

## 6. Оркестрация

### POST /api/rooms/{roomId}/orchestration/start
Запустить оркестрацию (подготовка). **Требует Bearer token.**

Работает только для `orchestration_type != "single"`. Обычно оркестрация запускается автоматически при `POST /messages`.

**Ответ:**
```json
{
  "status": "started",
  "roomId": 1,
  "orchestration_type": "circular"
}
```
**Ошибки:** 400 — single или нет агентов.

---

### POST /api/rooms/{roomId}/orchestration/stop
Остановить оркестрацию. **Требует Bearer token.**

**Ответ:**
```json
{
  "status": "stopped",
  "roomId": 1
}
```

---

## 7. События

### POST /api/rooms/{roomId}/events
Создать событие. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "description": "Найден клад!",
  "type": "user_event",
  "agentIds": ["1", "2"]
}
```
`agentIds` — опционально, пустой массив = для всей комнаты.

**Ответ:**
```json
{
  "id": "1",
  "type": "user_event",
  "agentIds": ["1", "2"],
  "description": "Найден клад!",
  "timestamp": "2025-02-16T12:00:00"
}
```

---

### POST /api/rooms/{roomId}/events/broadcast
Событие для всех агентов. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "description": "Наступила ночь",
  "type": "user_event"
}
```

**Специальный тип `user_message` или `chat`:**  
Если `type` = `"user_message"` или `"chat"`, `description` трактуется как сообщение пользователя — создаётся Message, broadcast, триггер ответов агентов. Для совместимости с фронтендами, отправляющими сообщения через events/broadcast.

**Ответ:** объект Event (agentIds — все агенты комнаты).

---

## 8. Сообщения

### POST /api/rooms/{roomId}/messages
Отправить сообщение в общий чат. **Рекомендуемый эндпоинт для multi-agent.** **Требует Bearer token.**

Сообщение видно всем агентам. Ответы приходят через WebSocket.

**Тело (JSON):**
```json
{
  "text": "Привет!",
  "sender": "user"
}
```

**Ответ:**
```json
{
  "id": "1",
  "text": "Привет!",
  "sender": "user",
  "timestamp": "2025-02-16T12:00:00",
  "agentId": null,
  "agentResponse": null
}
```
Ответы агентов — отдельные сообщения в WebSocket.

**Ошибки:** 400 — нет агентов в комнате.

---

### POST /api/rooms/{roomId}/agents/{agentId}/messages
Сообщение конкретному агенту (1-на-1). **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "text": "Выполни задание",
  "sender": "user"
}
```

**Ответ:**
```json
{
  "id": "1",
  "text": "Выполни задание",
  "sender": "user",
  "timestamp": "2025-02-16T12:00:00",
  "agentId": "1",
  "agentResponse": "Текст ответа агента..."
}
```
В режиме оркестрации `agentResponse` может быть `null` — ответы идут через WebSocket.

---

### GET /api/rooms/{roomId}/messages
Сообщения комнаты (ленивая загрузка). **Требует Bearer token.**

**Query:** `after_id` (int) — загрузить сообщения старше этого id; `limit` (1–100, default 20).

**Примеры:**
- `GET /api/rooms/1/messages` — последние 20
- `GET /api/rooms/1/messages?after_id=50&limit=20` — 20 сообщений старше id=50

**Ответ:**
```json
{
  "messages": [
    {
      "id": "45",
      "text": "Текст",
      "sender": "user",
      "agentId": "1",
      "timestamp": "2025-02-16T12:00:00"
    }
  ],
  "hasMore": true
}
```

---

## 9. Лента и скорость

### GET /api/rooms/{roomId}/feed
Лента (сообщения + события). **Требует Bearer token.**

**Query:** `limit` (1–100, default 20)

**Ответ:**
```json
{
  "items": [
    {
      "type": "event",
      "id": "1",
      "eventType": "interaction",
      "agentIds": ["1", "2"],
      "description": "Алиса и Боб поспорили",
      "timestamp": "2025-02-16T12:00:00"
    },
    {
      "type": "message",
      "id": "2",
      "text": "Привет!",
      "sender": "user",
      "agentId": "1",
      "timestamp": "2025-02-16T12:00:01"
    }
  ]
}
```

---

### PATCH /api/rooms/{roomId}/speed
Изменить скорость симуляции. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "speed": 2.0
}
```
`speed`: 0.1–10.0

**Ответ:** `{"speed": 2.0}`

---

## 10. Промпты

### GET /api/prompts/system
Системные промпты. **Без авторизации.**

**Ответ:**
```json
{
  "base": "Базовый системный промпт...",
  "single": "Промпт для single...",
  "orchestration": "Промпт для оркестрации..."
}
```

---

### GET /api/prompts/templates
Список шаблонов. **Без авторизации.**

**Ответ:**
```json
{
  "templates": ["minimal", "full", "expert", "character", "npc"],
  "descriptions": {
    "minimal": "Минимальный: имя и характер",
    "full": "Развёрнутый: характер и стиль речи",
    "expert": "Эксперт/консультант",
    "character": "Персонаж из произведения",
    "npc": "NPC в игре/симуляции"
  }
}
```

---

### GET /api/prompts/templates/{name}
Шаблон по имени. **Без авторизации.**

**Ответ:** `{"name": "minimal", "template": "Ты — {{name}}. Характер: {{character}}..."}`

**Ошибки:** 404 — шаблон не найден.

---

### POST /api/prompts/build
Собрать промпт из шаблона. **Без авторизации.**

**Тело (JSON):**
```json
{
  "template_name": "full",
  "name": "Копатыч",
  "character": "Добрый медведь",
  "speech_style": null,
  "traits": null,
  "phrases": null,
  "universe": null,
  "role": null,
  "expertise": null,
  "motivation": null,
  "attitude": null
}
```
Обязательные: `template_name`, `name`, `character`. Остальные — по шаблону.

**Ответ:** `{"prompt": "собранный текст...", "template": "full"}`

**Ошибки:** 400 — неверный template_name.

---

## 11. Шаблоны агентов (default-agents)

### GET /api/default-agents
Список шаблонов для создания агента. **Без авторизации.**

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Копатыч",
    "personality_preview": "Добрый медведь из «Смешариков»...",
    "avatar_url": null
  },
  {
    "id": 5,
    "name": "Нарратор",
    "personality_preview": "Рассказчик в ролевой игре...",
    "avatar_url": null
  }
]
```

---

### GET /api/default-agents/{id}
Шаблон по id (для формы). **Без авторизации.**

**Ответ:**
```json
{
  "id": 1,
  "name": "Копатыч",
  "character": "Добрый медведь из «Смешариков»...",
  "avatar": null
}
```
Готово для `POST /api/rooms/{roomId}/agents`.

**Ошибки:** 404 — шаблон не найден.

---

## 12. Каталог агентов

### GET /api/agents
Агенты в БД (созданные пользователями). **Без авторизации.**

**Ответ:** `[]` или `[{id, name, personality, avatar_url, state_vector}, ...]`

---

## 13. WebSocket

### WS /api/rooms/{roomId}/chat
Чат комнаты: сообщения и события в реальном времени.

**Подключение:**
```
ws://localhost:8000/api/rooms/{roomId}/chat?token={JWT}
```
JWT из `POST /api/auth/login`. В production: `wss://`.

**Коды закрытия:**
| Код  | Значение                                |
|------|-----------------------------------------|
| 4001 | Unauthorized (нет или неверный token)   |
| 4003 | Forbidden (нет доступа к комнате)       |

**Важно:** Подключать WebSocket **до** отправки сообщений, иначе broadcast не дойдёт.

---

#### Входящие от сервера

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

| Поле    | Тип    | Описание                                                                 |
|---------|--------|--------------------------------------------------------------------------|
| id      | string | ID сообщения                                                            |
| text    | string | Текст                                                                   |
| sender  | string | Отправитель (см. ниже)                                                  |
| agentId | string?| ID агента или `null`                                                    |
| timestamp| string| ISO 8601                                                                |

**Значения `sender` (режим circular):**
- Имя агента комнаты (например `"Гермиона Грейнджер"`)
- `"🎭 Рассказчик Нарратор"` — нарративные фрагменты, описание сцены
- `"📊 Сводка Суммаризатор"` — структурированная сводка раунда (Main ideas, Agreements и т.д.)
- `"Система"` — финальный синтез или «=== Раунд X завершён ===»
- `"user"` — сообщение пользователя

**event:**
```json
{
  "type": "event",
  "payload": {
    "id": "7",
    "eventType": "user_event",
    "agentIds": ["1", "2"],
    "description": "Алиса и Боб поспорили",
    "timestamp": "2025-02-16T14:31:00"
  }
}
```

**pong:**
```json
{"type": "pong", "payload": {}}
```

**error:**
```json
{"type": "error", "payload": {"message": "Описание ошибки"}}
```

---

#### Исходящие от клиента

**Ping (раз в 20–30 сек):**
```json
{"type": "ping"}
```

---

### WS /api/rooms/{roomId}/graph
Граф отношений: обновления рёбер в реальном времени.

**Подключение:**
```
ws://localhost:8000/api/rooms/{roomId}/graph?token={JWT}
```

**Коды закрытия:** те же (4001, 4003).

---

#### Входящие от сервера

| type       | Описание              |
|------------|-----------------------|
| connected  | Подключение           |
| edge_update| Обновление ребра      |
| pong       | Ответ на ping         |
| error      | Ошибка                |

**connected:**
```json
{
  "type": "connected",
  "payload": {
    "roomId": "1",
    "message": "Подключено к графу отношений"
  }
}
```

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

**Ping:** `{"type": "ping"}` → `{"type": "pong", "payload": {}}`

---

## 14. Сводная таблица эндпоинтов

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
| GET    | /api/rooms/{roomId}/agents/{agentId}/memories| Bearer|
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

## Связанные документы

- **CLIENT_GUIDE.md** — руководство по подключению
- **CLIENT_DOCUMENTATION.md** — обзор архитектуры и изменений
- **WEBSOCKET_CLIENT.md** — детали WebSocket
- **CONNECTION.md** — быстрый старт, CORS
