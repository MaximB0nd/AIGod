# WebSocket — документация для фронтенда (v1.0.0)

Подключение к реальному времени комнаты: чат (сообщения и события) и граф отношений.

**См. также:** `API_DOCS.md` — полный список REST-эндпоинтов.

---

## Базовый URL

| Режим        | URL                          |
|--------------|------------------------------|
| Локально     | `ws://localhost:8000`        |
| HTTPS-сервер | `wss://your-domain.com`      |

---

## 1. Чат комнаты

**Endpoint:** `WS /api/rooms/{roomId}/chat`

Поток сообщений (от пользователя, агентов, системы) и событий в комнате.

### Подключение

```
ws://localhost:8000/api/rooms/1/chat?token=YOUR_JWT_TOKEN
```

- `roomId` — ID комнаты (из `GET /api/rooms`)
- `token` — JWT из `POST /api/auth/login` (поле `token` в ответе)

### Коды закрытия

| Код  | Значение                                |
|------|-----------------------------------------|
| 4001 | Не авторизован (нет или неверный token) |
| 4003 | Нет доступа к комнате                   |

### Входящие сообщения от сервера

Все сообщения в формате JSON: `{ "type": string, "payload": object }`.

#### `connected` — успешное подключение

```json
{
  "type": "connected",
  "payload": {
    "roomId": "1",
    "message": "Подключено к чату комнаты"
  }
}
```

#### `message` — новое сообщение в чате

```json
{
  "type": "message",
  "payload": {
    "id": "42",
    "text": "Привет! Выполни задание.",
    "sender": "user",
    "agentId": "3",
    "timestamp": "2025-02-16T14:30:00",
    "agentResponse": null
  }
}
```

| Поле          | Тип    | Описание                                  |
|---------------|--------|-------------------------------------------|
| id            | string | ID сообщения                              |
| text          | string | Текст сообщения                           |
| sender        | string | `"user"` \| `"agent"` \| `"system"`      |
| agentId       | string?| ID агента (если сообщение к/от агента)    |
| timestamp     | string | ISO 8601                                  |
| agentResponse | string?| Ответ агента (если уже сгенерирован). В режиме оркестрации (`circular` и т.д.) ответы агентов приходят отдельными сообщениями с `sender: "agent"` |

#### `event` — событие в комнате

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

| Поле        | Тип     | Описание                    |
|-------------|---------|-----------------------------|
| id          | string  | ID события                  |
| eventType   | string  | Тип события                 |
| agentIds    | string[]| ID агентов, участвующих     |
| description | string  | Описание события            |
| timestamp   | string  | ISO 8601                    |

#### `pong` — ответ на ping

```json
{
  "type": "pong",
  "payload": {}
}
```

#### `error` — ошибка сервера

```json
{
  "type": "error",
  "payload": {
    "message": "Описание ошибки"
  }
}
```

### Исходящие сообщения (клиент → сервер)

Единственная нужная команда — **ping** для поддержания соединения:

```json
{"type": "ping"}
```

В ответ придёт `{"type": "pong", "payload": {}}`.

Отправляй ping раз в 20–30 секунд.

---

## 2. Граф отношений

**Endpoint:** `WS /api/rooms/{roomId}/graph`

Поток обновлений рёбер графа отношений между агентами.

### Подключение

```
ws://localhost:8000/api/rooms/1/graph?token=YOUR_JWT_TOKEN
```

### Входящие сообщения

#### `connected`

```json
{
  "type": "connected",
  "payload": {
    "roomId": "1",
    "message": "Подключено к графу отношений"
  }
}
```

#### `edge_update` — обновление ребра

Приходит при изменении отношения между двумя агентами (в т.ч. через `PATCH /api/rooms/{roomId}/relationships`).

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

| Поле          | Тип    | Описание                              |
|---------------|--------|---------------------------------------|
| roomId        | string | ID комнаты                            |
| from          | string | ID агента 1 (исток ребра)            |
| to            | string | ID агента 2 (конец ребра)            |
| sympathyLevel | number | Уровень симпатии от -1 до 1           |

Используй это для обновления графа (D3.js, vis-network и т.п.) без перезапроса всего графа.

#### `pong`, `error` — такие же, как в чате

---

## Примеры кода

### JavaScript (нативный WebSocket)

```javascript
const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

// 1. Логин, получение токена
const loginRes = await fetch(`${API_URL}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com', password: 'password123' }),
});
const { token } = await loginRes.json();

// 2. Подключение к чату комнаты
const roomId = 1;
const chatWs = new WebSocket(`${WS_URL}/api/rooms/${roomId}/chat?token=${token}`);

chatWs.onopen = () => {
  console.log('Chat WebSocket connected');
};

chatWs.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case 'connected':
      console.log('Room:', msg.payload.roomId);
      break;
    case 'message':
      addMessageToUI(msg.payload);
      break;
    case 'event':
      addEventToUI(msg.payload);
      break;
    case 'pong':
      // keepalive OK
      break;
    case 'error':
      console.error('WS error:', msg.payload.message);
      break;
  }
};

chatWs.onclose = (event) => {
  if (event.code === 4001) console.error('Unauthorized');
  if (event.code === 4003) console.error('No access to room');
};

// Ping каждые 25 сек
const pingInterval = setInterval(() => {
  if (chatWs.readyState === WebSocket.OPEN) {
    chatWs.send(JSON.stringify({ type: 'ping' }));
  }
}, 25000);

chatWs.onclose = () => clearInterval(pingInterval);
```

### Граф (React-подобный пример)

```javascript
const graphWs = new WebSocket(`${WS_URL}/api/rooms/${roomId}/graph?token=${token}`);

graphWs.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'edge_update') {
    const { from, to, sympathyLevel } = msg.payload;
    // Обновить ребро в D3/vis-network
    updateGraphEdge(from, to, sympathyLevel);
  }
};
```

### TypeScript типы

```typescript
type ChatMessage = {
  type: 'connected' | 'message' | 'event' | 'pong' | 'error';
  payload: {
    roomId?: string;
    message?: string;
    id?: string;
    text?: string;
    sender?: 'user' | 'agent' | 'system';
    agentId?: string | null;
    timestamp?: string;
    agentResponse?: string | null;
    eventType?: string;
    agentIds?: string[];
    description?: string;
  };
};

type GraphMessage = {
  type: 'connected' | 'edge_update' | 'pong' | 'error';
  payload: {
    roomId?: string;
    message?: string;
    from?: string;
    to?: string;
    sympathyLevel?: number;
  };
};
```

---

## Рекомендации

1. **Смена комнаты** — закрой текущие WS и подключись к новым URL с новым `roomId`.
2. **Смена токена** — после refresh токена переподключай WebSocket с новым `token`.
3. **Reconnect** — при `onclose` можно делать `setTimeout` и повторное подключение (без спама).
4. **Ping** — отправляй `{"type": "ping"}` раз в 20–30 сек, чтобы соединение не рвалось.
5. **HTTPS** — в production используй `wss://` на том же хосте, что и `https://`.
