# Требования к API бэкенда — «Виртуальный мир: симулятор живых существ»

Список ручек для веб-приложения по ТЗ хакатона «КИБЕР РЫВОК».  
Все операции с агентами привязаны к **текущей комнате** (room).

---

## Общие типы (схемы)

```ts
Room = {
  id: string
  name: string
  description?: string
  speed?: number
  createdAt: string
}

AgentSummary = {
  id: string
  name: string
  avatar?: string
  mood: { mood: string; level: number; icon?: string; color?: string }
}

Agent = AgentSummary & {
  character: string
  keyMemories?: Memory[]
  plans?: Plan[]
}

Memory = { id: string; content: string; timestamp: string; importance?: number }
Plan = { id: string; description: string; status: 'pending' | 'in_progress' | 'done' }
Relationship = { from: string; to: string; agentName?: string; sympathyLevel: number }

Event = {
  id: string
  type: string
  agentIds: string[]
  description: string
  timestamp: string
  moodImpact?: Record<string, number>
}

Message = {
  id: string
  text: string
  sender: 'user' | 'agent'
  agentId?: string
  timestamp: string
}
```

**Текущая комната:** передаётся через `roomId` в URL или заголовок `X-Room-Id`. После логина пользователь выбирает/создаёт комнату.

---

## 1. Регистрация и авторизация

### 1.1 Регистрация

**`POST /api/auth/register`**

**Отправлять:**
```json
{
  "email": "user@example.com",
  "password": "string",
  "username": "string"
}
```

**Получать:**
```json
{
  "id": "uuid",
  "email": "string",
  "username": "string",
  "token": "jwt_token",
  "refreshToken": "string"
}
```

---

### 1.2 Вход в аккаунт

**`POST /api/auth/login`**

**Отправлять:**
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Получать:**
```json
{
  "id": "uuid",
  "email": "string",
  "username": "string",
  "token": "jwt_token",
  "refreshToken": "string"
}
```

---

## 2. Комнаты

*Нужны для выбора «текущей комнаты» и работы с агентами.*

### 2.1 Создать комнату

**`POST /api/rooms`**

**Отправлять:**
```json
{
  "name": "string",
  "description": "string (опционально)"
}
```

**Получать:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "speed": 1.0,
  "createdAt": "ISO8601"
}
```

---

### 2.2 Список комнат пользователя

**`GET /api/rooms`**

**Отправлять:** ничего

**Получать:**
```json
{
  "rooms": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "speed": 1.0,
      "createdAt": "ISO8601"
    }
  ]
}
```

---

### 2.3 Получить информацию по текущей комнате

**`GET /api/rooms/{roomId}`**

**Отправлять:** ничего

**Получать:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "speed": 1.0,
  "createdAt": "ISO8601",
  "agentCount": 5
}
```

---

### 2.4 Изменить информацию о текущей комнате

**`PATCH /api/rooms/{roomId}`**

**Отправлять:**
```json
{
  "name": "string (опционально)",
  "description": "string (опционально)",
  "speed": 1.0
}
```

**Получать:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "speed": 1.0,
  "updatedAt": "ISO8601"
}
```

---

### 2.5 Удалить комнату по id

**`DELETE /api/rooms/{roomId}`**

**Отправлять:** ничего

**Получать:**
```json
{
  "success": true
}
```
или `204 No Content`

---

## 3. Агенты (в контексте комнаты)

*Все ручки ниже используют `roomId` — текущая комната.*

### 3.1 Получить всех агентов текущей комнаты

**`GET /api/rooms/{roomId}/agents`**

**Отправлять:** ничего

**Получать:**
```json
{
  "agents": [
    {
      "id": "uuid",
      "name": "string",
      "avatar": "url",
      "mood": { "mood": "happy", "level": 0.8, "icon": "😊", "color": "#4ade80" }
    }
  ]
}
```

---

### 3.2 Получить полную информацию по агенту по его id

**`GET /api/rooms/{roomId}/agents/{agentId}`**

**Отправлять:** ничего

**Получать:**
```json
{
  "id": "uuid",
  "name": "string",
  "avatar": "url",
  "mood": { "mood": "happy", "level": 0.8, "icon": "😊", "color": "#4ade80" },
  "character": "Описание характера агента",
  "keyMemories": [
    { "id": "uuid", "content": "string", "timestamp": "ISO8601", "importance": 0.9 }
  ],
  "plans": [
    { "id": "uuid", "description": "string", "status": "in_progress" }
  ]
}
```

---

### 3.3 Создать своего агента и прикрепить к текущей комнате

**`POST /api/rooms/{roomId}/agents`**

**Отправлять:**
```json
{
  "name": "string",
  "character": "Описание личности, характера",
  "avatar": "url (опционально)"
}
```

**Получать:**
```json
{
  "id": "uuid",
  "name": "string",
  "character": "string",
  "avatar": "url",
  "mood": { "mood": "neutral", "level": 0.5, "icon": "😐", "color": "#94a3b8" }
}
```

---

### 3.4 Удалить агента

**`DELETE /api/rooms/{roomId}/agents/{agentId}`**

**Отправлять:** ничего

**Получать:**
```json
{
  "success": true
}
```
или `204 No Content`

---

### 3.5 Получить воспоминания текущего агента текущей комнаты

**`GET /api/rooms/{roomId}/agents/{agentId}/memories`**

**Отправлять:** query: `?limit=20&offset=0`

**Получать:**
```json
{
  "memories": [
    { "id": "uuid", "content": "string", "timestamp": "ISO8601", "importance": 0.7 }
  ],
  "total": 42
}
```

---

### 3.6 Получить взаимоотношения агентов текущей комнаты

**`GET /api/rooms/{roomId}/relationships`**

**Отправлять:** ничего

**Получать:**
```json
{
  "nodes": [
    { "id": "uuid", "name": "string", "avatar": "url", "mood": { "mood": "happy", "level": 0.8, "color": "#4ade80" } }
  ],
  "edges": [
    { "from": "agentId1", "to": "agentId2", "sympathyLevel": 0.7 }
  ]
}
```
`sympathyLevel`: от -1 до 1 — для цвета ребра в графе.

---

### 3.7 Получить планы текущего агента текущей комнаты

**`GET /api/rooms/{roomId}/agents/{agentId}/plans`**

**Отправлять:** ничего

**Получать:**
```json
{
  "plans": [
    { "id": "uuid", "description": "string", "status": "pending" | "in_progress" | "done" }
  ]
}
```

---

### 3.8 Написать событие, которое произошло в комнате

**`POST /api/rooms/{roomId}/events`**

**Отправлять:**
```json
{
  "description": "Найден клад!",
  "type": "user_event",
  "agentIds": ["id1", "id2"]
}
```
`agentIds` — опционально. Если пусто — событие для всей комнаты.

**Получать:**
```json
{
  "id": "uuid",
  "type": "user_event",
  "agentIds": ["id1", "id2"],
  "description": "Найден клад!",
  "timestamp": "ISO8601"
}
```

---

### 3.9 Получить последние 20 сообщений и событий текущей комнаты

**`GET /api/rooms/{roomId}/feed`**

**Отправлять:** query: `?limit=20` (по умолчанию 20)

**Получать:**
```json
{
  "items": [
    {
      "type": "event",
      "id": "uuid",
      "eventType": "interaction",
      "agentIds": ["id1", "id2"],
      "description": "Алиса и Боб поспорили",
      "timestamp": "ISO8601"
    },
    {
      "type": "message",
      "id": "uuid",
      "text": "Привет!",
      "sender": "user",
      "agentId": null,
      "timestamp": "ISO8601"
    }
  ]
}
```
Объединённая лента: сообщения и события в хронологическом порядке.

---

## 4. Сообщения (вмешательство пользователя)

*По ТЗ: «Поле для отправки сообщения конкретному агенту».*

### 4.1 Отправить сообщение агенту

**`POST /api/rooms/{roomId}/agents/{agentId}/messages`**

**Отправлять:**
```json
{
  "text": "Привет! Выполни задание: сходи в магазин.",
  "sender": "user"
}
```

**Получать:**
```json
{
  "id": "uuid",
  "text": "string",
  "sender": "user",
  "timestamp": "ISO8601",
  "agentResponse": "Ответ агента (опционально, если бэкенд сразу генерирует)"
}
```

---

### 4.2 Отправка события всем агентам текущей комнаты

**`POST /api/rooms/{roomId}/events/broadcast`**

**Отправлять:**
```json
{
  "description": "Наступила ночь, луна светит ярко",
  "type": "user_event"
}
```
Событие доставляется всем агентам комнаты.

**Получать:**
```json
{
  "id": "uuid",
  "type": "user_event",
  "agentIds": ["id1", "id2", "id3"],
  "description": "Наступила ночь, луна светит ярко",
  "timestamp": "ISO8601"
}
```
`agentIds` — список всех агентов комнаты, которым отправлено событие.

---

## 5. Симуляция (дополнительно для проекта)

*По ТЗ: «Слайдер скорость времени».*

### 5.1 Изменить скорость симуляции комнаты

**`PATCH /api/rooms/{roomId}/speed`**

**Отправлять:**
```json
{
  "speed": 2.0
}
```

**Получать:**
```json
{
  "speed": 2.0
}
```

---

## 6. WebSocket

**Клиент принимает у себя сообщения и события, которые произошли в комнате.**

### Подключение

**`ws://.../api/rooms/{roomId}/stream`**

- Подключение с токеном авторизации (query: `?token=jwt` или в заголовке).
- После подключения клиент получает поток сообщений и событий в реальном времени.

### Формат входящих сообщений

```json
{
  "type": "event",
  "payload": {
    "id": "uuid",
    "eventType": "interaction",
    "agentIds": ["id1", "id2"],
    "description": "string",
    "timestamp": "ISO8601",
    "moodImpact": {}
  }
}
```

```json
{
  "type": "message",
  "payload": {
    "id": "uuid",
    "text": "string",
    "sender": "user" | "agent",
    "agentId": "uuid",
    "timestamp": "ISO8601"
  }
}
```

```json
{
  "type": "agent_update",
  "payload": {
    "agentId": "uuid",
    "mood": { "mood": "happy", "level": 0.8, "icon": "😊", "color": "#4ade80" }
  }
}
```

Клиент подписывается на комнату по `roomId` и получает все новые события и сообщения в реальном времени.

---

## Сводная таблица

| № | Категория | Метод | Путь |
|---|-----------|-------|------|
| 1 | Регистрация | POST | `/api/auth/register` |
| 2 | Вход | POST | `/api/auth/login` |
| 3 | Комнаты | POST | `/api/rooms` |
| 4 | Комнаты | GET | `/api/rooms` |
| 5 | Комнаты | GET | `/api/rooms/{roomId}` |
| 6 | Комнаты | PATCH | `/api/rooms/{roomId}` |
| 7 | Комнаты | DELETE | `/api/rooms/{roomId}` |
| 8 | Агенты | GET | `/api/rooms/{roomId}/agents` |
| 9 | Агенты | GET | `/api/rooms/{roomId}/agents/{agentId}` |
| 10 | Агенты | POST | `/api/rooms/{roomId}/agents` |
| 11 | Агенты | DELETE | `/api/rooms/{roomId}/agents/{agentId}` |
| 12 | Агенты | GET | `/api/rooms/{roomId}/agents/{agentId}/memories` |
| 13 | Агенты | GET | `/api/rooms/{roomId}/relationships` |
| 14 | Агенты | GET | `/api/rooms/{roomId}/agents/{agentId}/plans` |
| 15 | События | POST | `/api/rooms/{roomId}/events` |
| 16 | События | POST | `/api/rooms/{roomId}/events/broadcast` |
| 17 | Лента | GET | `/api/rooms/{roomId}/feed` |
| 18 | Сообщения | POST | `/api/rooms/{roomId}/agents/{agentId}/messages` |
| 19 | Симуляция | PATCH | `/api/rooms/{roomId}/speed` |
| — | WebSocket | WS | `/api/rooms/{roomId}/stream` |

**Итого: 19 REST-ручек + WebSocket**

---

## Примечания

1. **Текущая комната** — пользователь выбирает комнату после входа. `roomId` передаётся в URL или хранится в состоянии приложения.
2. **Авторизация** — все ручки (кроме register/login) требуют заголовок `Authorization: Bearer <token>`.
3. **WebSocket** — при смене комнаты клиент переподключается к новому `roomId`.
