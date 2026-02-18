# Требования к API бэкенда — AIgod

Актуальный контракт по CLIENT_DOCUMENTATION.md и CLIENT_GUIDE.md.  
Все операции с агентами привязаны к **текущей комнате** (room).

---

## Общие типы (схемы)

```ts
Room = {
  id: string
  name: string
  description?: string
  speed?: number
  orchestration_type?: 'single' | 'circular' | 'narrator' | 'full_context'
  createdAt: string
  updatedAt?: string
  agentCount?: number
}

AgentSummary = {
  id: string
  name: string
  avatar?: string
  character?: string
  mood?: { mood: string; level: number; icon?: string; color?: string }
}

Agent = AgentSummary & {
  character: string
  keyMemories?: Memory[]
  plans?: Plan[]
}

Message = {
  id: string
  text: string
  sender: 'user' | 'agent' | 'system'
  agentId?: string | null
  timestamp: string
}

Relationship = { from: string; to: string; agentName?: string; sympathyLevel: number }
```

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
  "id": "string",
  "email": "string",
  "username": "string",
  "token": "jwt_token"
}
```

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
  "id": "string",
  "email": "string",
  "username": "string",
  "token": "jwt_token"
}
```

### 1.3 Текущий пользователь

**`GET /api/auth/me`**  
Заголовок: `Authorization: Bearer <token>`

---

## 2. Комнаты

### 2.1 Создать комнату

**`POST /api/rooms`**

**Отправлять:**
```json
{
  "name": "string",
  "description": "string (опционально)",
  "orchestration_type": "single | circular | narrator | full_context"
}
```

**Получать:**
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "speed": 1.0,
  "orchestration_type": "circular",
  "createdAt": "ISO8601",
  "updatedAt": null,
  "agentCount": null
}
```

### 2.2 Список комнат

**`GET /api/rooms`**

**Получать:** `{ "rooms": [ ... ] }`

### 2.3 Получить комнату

**`GET /api/rooms/{id}`**

### 2.4 Обновить комнату

**`PATCH /api/rooms/{id}`**

### 2.5 Удалить комнату

**`DELETE /api/rooms/{id}`**

---

## 3. Агенты в комнате

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/rooms/{id}/agents | Список агентов |
| GET | /api/rooms/{id}/agents/{aid} | Агент по ID |
| POST | /api/rooms/{id}/agents | Добавить агента |
| DELETE | /api/rooms/{id}/agents/{aid} | Удалить агента |

**Создание агента:**
```json
POST /api/rooms/{roomId}/agents
{
  "name": "Маркетолог",
  "character": "Эксперт по продвижению...",
  "avatar": "https://..."
}
```

---

## 4. Сообщения и лента

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/rooms/{id}/messages | Сообщение в общий чат |
| GET | /api/rooms/{id}/messages | История сообщений |
| GET | /api/rooms/{id}/feed | Лента (сообщения + события) |
| POST | /api/rooms/{id}/agents/{aid}/messages | Сообщение конкретному агенту |

**Отправка в общий чат:**
```json
POST /api/rooms/{roomId}/messages
{
  "text": "Привет!",
  "sender": "user"
}
```

**Ответ:** `{ id, text, sender, timestamp, agentId, agentResponse }`  
Ответы агентов приходят по WebSocket.

**История:** `GET /api/rooms/{id}/messages?limit=20&after_id=100`  
Ответ: `{ messages: [...], hasMore }`

---

## 5. Отношения и модель

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/rooms/{id}/relationships | Отношения между агентами |
| PATCH | /api/rooms/{id}/relationships | Обновить отношение |
| GET | /api/rooms/{id}/relationship-model | Граф + статистика |
| GET | /api/rooms/{id}/emotional-state | Эмоциональное состояние |
| GET | /api/rooms/{id}/context-memory | Сводка по памяти |

---

## 6. Оркестрация

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/rooms/{id}/orchestration/start | Запустить оркестрацию |
| POST | /api/rooms/{id}/orchestration/stop | Остановить оркестрацию |

---

## 7. События

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/rooms/{id}/events | Создать событие |
| POST | /api/rooms/{id}/events/broadcast | Broadcast события |

---

## 8. Шаблоны и промпты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/default-agents | Шаблоны агентов |
| GET | /api/default-agents/{id} | Шаблон по ID |
| GET | /api/prompts/system | Системные промпты |
| GET | /api/prompts/templates | Шаблоны промптов |
| POST | /api/prompts/build | Сборка промпта |
| GET | /api/agents | Каталог агентов |

---

## 9. WebSocket

### Чат
```
ws://host/api/rooms/{roomId}/chat?token={JWT}
```
Входящие: `connected`, `message`, `event`, `pong`, `error`  
Клиент отправляет `{"type": "ping"}` раз в 20–30 сек.

**Структура message:**
```json
{
  "type": "message",
  "payload": {
    "id": "124",
    "text": "...",
    "sender": "Маркетолог",
    "agentId": "1",
    "timestamp": "2025-02-18T12:00:05"
  }
}
```

### Граф отношений
```
ws://host/api/rooms/{roomId}/graph?token={JWT}
```
Входящие: `connected`, `edge_update`, `pong`, `error`

---

## 10. Типичный сценарий

1. **Логин:** `POST /api/auth/login` → сохранить `token`
2. **Подключить WebSocket** к чату **до** отправки сообщений
3. **Комната:** `POST /api/rooms` с `orchestration_type`
4. **Агенты:** `POST /api/rooms/{id}/agents` или через default-agents
5. **Сообщение:** `POST /api/rooms/{id}/messages` → ответы агентов придут по WebSocket
6. **История:** `GET /api/rooms/{id}/messages` или `/feed`

---

## Режимы оркестрации

| Режим | Поведение |
|-------|-----------|
| **single** | Каждый агент отвечает отдельно (по умолчанию) |
| **circular** | Агенты по кругу, до 5 раундов, фокус на запросе |
| **narrator** | Один рассказчик ведёт историю, остальные — персонажи |
| **full_context** | Обсуждение с суммаризацией раундов |
