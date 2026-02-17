# AIgod API — документация

**Базовый URL:** `http://localhost:8000`  
**Swagger UI:** `/docs`  
**ReDoc:** `/redoc`  

**Авторизация:** все эндпоинты кроме `register` и `login` требуют заголовок:
```
Authorization: Bearer <token>
```

---

## Системные

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

### GET /api/test-db
Проверка подключения к БД.

**Ответ:**
```json
{
  "status": "база подключена"
}
```

---

## Авторизация

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

| Поле      | Тип    | Обязательно | Описание                              |
|-----------|--------|-------------|---------------------------------------|
| email     | string | да          | Валидный email                        |
| password  | string | да          | Минимум 8 символов                    |
| username  | string | нет         | По умолчанию — часть до @ из email    |

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

---

## Комнаты

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
  "description": "Опционально"
}
```

**Ответ:**
```json
{
  "id": "1",
  "name": "Новая комната",
  "description": "Опционально",
  "speed": 1.0,
  "createdAt": "2025-02-16T12:00:00",
  "updatedAt": null,
  "agentCount": null
}
```

---

### GET /api/rooms/{roomId}
Информация о комнате. **Требует Bearer token.**

**Ответ:**
```json
{
  "id": "1",
  "name": "Моя комната",
  "description": "Описание",
  "speed": 1.0,
  "createdAt": "2025-02-16T12:00:00",
  "updatedAt": null,
  "agentCount": 5
}
```

---

### PATCH /api/rooms/{roomId}
Изменить комнату. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "name": "Новое имя",
  "description": "Новое описание",
  "speed": 2.0
}
```
Все поля опциональны.

**Ответ:** объект Room (как в GET).

---

### DELETE /api/rooms/{roomId}
Удалить комнату. **Требует Bearer token.**

**Ответ:** `204 No Content`

---

## Агенты в комнате

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
Полная информация по агенту. **Требует Bearer token.**

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
      "content": "Содержимое воспоминания",
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
  ]
}
```

---

### POST /api/rooms/{roomId}/agents
Создать агента в комнате или добавить существующего. **Требует Bearer token.**

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

| Поле     | Тип   | Обязательно | Описание                              |
|----------|-------|-------------|---------------------------------------|
| name     | string| да          | Имя агента                            |
| character| string| нет*        | Описание личности (*обязательно при создании) |
| avatar   | string| нет         | URL аватара                           |
| agentId  | int   | нет         | ID существующего агента для добавления|

**Ответ:** объект AgentSummary (id, name, avatar, mood).

---

### DELETE /api/rooms/{roomId}/agents/{agentId}
Удалить агента из комнаты. **Требует Bearer token.**

**Ответ:** `204 No Content`

---

### GET /api/rooms/{roomId}/agents/{agentId}/memories
Воспоминания агента. **Требует Bearer token.**

**Query-параметры:**
| Параметр | Тип  | По умолчанию | Описание    |
|----------|------|--------------|-------------|
| limit    | int  | 20           | 1–100       |
| offset   | int  | 0            | Смещение    |

**Ответ:**
```json
{
  "memories": [
    {
      "id": "1",
      "content": "Текст воспоминания",
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
      "description": "Описание плана",
      "status": "pending"
    }
  ]
}
```
`status`: `"pending"` | `"in_progress"` | `"done"`

---

### PATCH /api/rooms/{roomId}/relationships
Обновить ребро графа отношений. Рассылает обновление в WebSocket графа. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "agent1Id": 1,
  "agent2Id": 2,
  "sympathyLevel": 0.7
}
```
`sympathyLevel`: -1.0 .. 1.0

**Ответ:** `{ "from": "1", "to": "2", "sympathyLevel": 0.7 }`

---

### GET /api/rooms/{roomId}/relationships
Связи агентов в комнате. **Требует Bearer token.**

**Ответ:**
```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Копатыч",
      "avatar": "https://...",
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
`sympathyLevel`: от -1 до 1.

---

## События

### POST /api/rooms/{roomId}/events
Создать событие в комнате. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "description": "Найден клад!",
  "type": "user_event",
  "agentIds": ["1", "2"]
}
```
`agentIds` — опционально. Пустой массив = для всей комнаты.

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
Событие для всех агентов комнаты. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "description": "Наступила ночь",
  "type": "user_event"
}
```

**Ответ:** объект Event (в `agentIds` — все агенты комнаты).

---

## Лента

### GET /api/rooms/{roomId}/feed
Лента сообщений и событий. **Требует Bearer token.**

**Query-параметры:**
| Параметр | Тип | По умолчанию | Описание       |
|----------|-----|--------------|----------------|
| limit    | int | 20           | 1–100, кол-во  |

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

## Сообщения

### POST /api/rooms/{roomId}/agents/{agentId}/messages
Отправить сообщение агенту. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "text": "Привет! Выполни задание.",
  "sender": "user"
}
```

**Ответ:**
```json
{
  "id": "1",
  "text": "Привет! Выполни задание.",
  "sender": "user",
  "timestamp": "2025-02-16T12:00:00",
  "agentId": "1",
  "agentResponse": null
}
```
`agentResponse` — пока `null`, в будущем — ответ LLM.

---

## Симуляция

### PATCH /api/rooms/{roomId}/speed
Изменить скорость симуляции. **Требует Bearer token.**

**Тело (JSON):**
```json
{
  "speed": 2.0
}
```
`speed`: 0.1–10.0

**Ответ:**
```json
{
  "speed": 2.0
}
```

---

## Каталог агентов

### GET /api/agents
Все агенты в БД (для добавления в комнату). **Без авторизации.**

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Копатыч",
    "personality": "Описание характера...",
    "avatar_url": "(нет аватара)",
    "state_vector": {}
  }
]
```

---

## WebSocket

### WS /api/rooms/{roomId}/chat
Чат комнаты: сообщения от агентов и системные события в реальном времени.

**Подключение:** `ws://localhost:8000/api/rooms/1/chat?token=JWT`

**Входящие от сервера:**
- `{"type": "connected", "payload": {"roomId": "1", ...}}` — при подключении
- `{"type": "message", "payload": {"id", "text", "sender", "agentId?", "timestamp", "agentResponse?"}}` — новое сообщение
- `{"type": "event", "payload": {"id", "eventType", "agentIds", "description", "timestamp"}}` — событие
- `{"type": "pong", "payload": {}}` — ответ на ping

**Ping:** отправь `{"type": "ping"}` для поддержания соединения.

---

### WS /api/rooms/{roomId}/graph
Граф отношений: обновления рёбер в реальном времени.

**Подключение:** `ws://localhost:8000/api/rooms/1/graph?token=JWT`

**Входящие от сервера:**
- `{"type": "connected", "payload": {"roomId": "1", ...}}` — при подключении
- `{"type": "edge_update", "payload": {"roomId", "from", "to", "sympathyLevel"}}` — обновление ребра
- `{"type": "pong", "payload": {}}` — ответ на ping

Клиент обновляет D3.js/vis-network по `edge_update` без перезапроса всего графа.

---

## Сводная таблица

| Метод | Путь | Авторизация |
|-------|------|-------------|
| GET | / | — |
| GET | /api/ | — |
| GET | /api/test-db | — |
| POST | /api/auth/register | — |
| POST | /api/auth/login | — |
| GET | /api/auth/me | Bearer |
| GET | /api/rooms | Bearer |
| POST | /api/rooms | Bearer |
| GET | /api/rooms/{roomId} | Bearer |
| PATCH | /api/rooms/{roomId} | Bearer |
| DELETE | /api/rooms/{roomId} | Bearer |
| GET | /api/rooms/{roomId}/agents | Bearer |
| GET | /api/rooms/{roomId}/agents/{agentId} | Bearer |
| POST | /api/rooms/{roomId}/agents | Bearer |
| DELETE | /api/rooms/{roomId}/agents/{agentId} | Bearer |
| GET | /api/rooms/{roomId}/agents/{agentId}/memories | Bearer |
| GET | /api/rooms/{roomId}/agents/{agentId}/plans | Bearer |
| PATCH | /api/rooms/{roomId}/relationships | Bearer |
| GET | /api/rooms/{roomId}/relationships | Bearer |
| POST | /api/rooms/{roomId}/events | Bearer |
| POST | /api/rooms/{roomId}/events/broadcast | Bearer |
| GET | /api/rooms/{roomId}/feed | Bearer |
| POST | /api/rooms/{roomId}/agents/{agentId}/messages | Bearer |
| PATCH | /api/rooms/{roomId}/speed | Bearer |
| GET | /api/agents | — |
| WS | /api/rooms/{roomId}/chat | token в query |
| WS | /api/rooms/{roomId}/graph | token в query |
