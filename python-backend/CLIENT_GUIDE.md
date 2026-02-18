# Руководство подключения клиента к AIgod API

Полная документация для интеграции фронтенда и мобильного клиента. Следуйте шагам по порядку — всё будет работать.

---

## Оглавление

1. [Быстрый старт](#1-быстрый-старт)
2. [Требования и настройка сервера](#2-требования-и-настройка-сервера)
3. [Авторизация](#3-авторизация)
4. [Комнаты и агенты](#4-комнаты-и-агенты)
5. [Сообщения и чат](#5-сообщения-и-чат)
6. [WebSocket — real-time](#6-websocket--real-time)
7. [Граф отношений](#7-граф-отношений)
8. [Режимы оркестрации](#8-режимы-оркестрации)
9. [Пример полной интеграции](#9-пример-полной-интеграции)
10. [Устранение неполадок](#10-устранение-неполадок)

---

## 1. Быстрый старт

### Чек-лист подключения

- [ ] Сервер запущен (`uvicorn app.main:app`)
- [ ] Переменные `YANDEX_CLOUD_FOLDER` и `YANDEX_CLOUD_API_KEY` заданы в `.env`
- [ ] Клиент подключается по `http://localhost:8000` (или ваш URL)
- [ ] **WebSocket подключается ДО отправки сообщений** — иначе ответы агентов не придут
- [ ] Все защищённые запросы содержат заголовок `Authorization: Bearer <token>`

### Минимальный flow

```
1. POST /api/auth/login        → токен
2. ws://host/api/rooms/{id}/chat?token=...  → подключить
3. POST /api/rooms/{id}/messages           → отправить сообщение
4. Получить ответы по WebSocket (type: "message")
```

---

## 2. Требования и настройка сервера

### URL

| Режим | REST API | WebSocket |
|-------|----------|-----------|
| Локально | `http://localhost:8000` | `ws://localhost:8000` |
| Production | `https://your-domain.com` | `wss://your-domain.com` |

### Документация API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Переменные окружения (сервер)

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `YANDEX_CLOUD_FOLDER` | Да* | ID папки в Yandex Cloud |
| `YANDEX_CLOUD_API_KEY` | Да* | API-ключ Yandex GPT |
| `SECRET_KEY` | Нет | JWT secret (по умолчанию есть) |
| `SQLITE_DB_PATH` | Нет | Путь к БД (по умолчанию `agents.db`) |
| `CHROMA_PERSIST_DIR` | Нет | Путь к ChromaDB для памяти (по умолчанию `./chroma_db`) |

\* Без Yandex ключей оркестрация не запустится — сработает fallback в режим single.

### Запуск сервера

```bash
cd python-backend
pip install -r requirements.txt
# Создать .env с YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0
```

---

## 3. Авторизация

### Регистрация

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "username": "user"
}
```

Ответ:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "id": "1",
  "email": "user@example.com",
  "username": "user"
}
```

### Логин

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

Ответ: тот же формат с `token`.

### Использование токена

Добавить ко **всем** защищённым запросам:

```
Authorization: Bearer <token>
```

Токен действителен `ACCESS_TOKEN_EXPIRE_MINUTES` минут (по умолчанию 30).

### Проверка сессии

```http
GET /api/auth/me
Authorization: Bearer <token>
```

---

## 4. Комнаты и агенты

### Создание комнаты

```http
POST /api/rooms
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Обсуждение стартапа",
  "description": "Идеи и планы",
  "orchestration_type": "circular"
}
```

Ответ:

```json
{
  "id": "1",
  "name": "Обсуждение стартапа",
  "description": "Идеи и планы",
  "speed": 1.0,
  "orchestration_type": "circular",
  "createdAt": "2025-02-18T12:00:00",
  "updatedAt": null,
  "agentCount": null
}
```

**orchestration_type:**

- `single` — каждый агент отвечает отдельно (по умолчанию)
- `circular` — агенты общаются по кругу, до 5 раундов
- `narrator` — один рассказчик ведёт историю
- `full_context` — обсуждение с суммаризацией

### Список комнат

```http
GET /api/rooms
Authorization: Bearer <token>
```

Ответ: `{ "rooms": [ ... ] }`

### Добавление агента

**Из шаблона:**

```http
GET /api/default-agents
GET /api/default-agents/1
```

**Создание в комнате:**

```http
POST /api/rooms/{roomId}/agents
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Маркетолог",
  "character": "Эксперт по продвижению. Любит данные и A/B тесты.",
  "avatar": "https://..."
}
```

Ответ: `{ "id": "1", "name": "Маркетолог", "avatar": "..." }`

### Список агентов комнаты

```http
GET /api/rooms/{roomId}/agents
Authorization: Bearer <token>
```

---

## 5. Сообщения и чат

### Сообщение в общий чат (все агенты)

```http
POST /api/rooms/{roomId}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Как лучше провести маркетинговую кампанию?",
  "sender": "user"
}
```

Ответ (сразу):

```json
{
  "id": "123",
  "text": "Как лучше провести маркетинговую кампанию?",
  "sender": "user",
  "timestamp": "2025-02-18T12:00:00",
  "agentId": null,
  "agentResponse": null
}
```

**Ответы агентов приходят по WebSocket** (см. раздел 6). В режиме `circular`/`narrator`/`full_context` сначала идёт обсуждение агентов, затем финальный ответ от «Системы».

### Сообщение конкретному агенту

```http
POST /api/rooms/{roomId}/agents/{agentId}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Расскажи подробнее",
  "sender": "user"
}
```

Ответ содержит `agentResponse` с текстом ответа агента.

### История сообщений

```http
GET /api/rooms/{roomId}/messages?limit=20
GET /api/rooms/{roomId}/messages?after_id=100&limit=20
Authorization: Bearer <token>
```

Ответ:

```json
{
  "messages": [
    {
      "id": "1",
      "text": "Текст",
      "sender": "user",
      "agentId": null,
      "timestamp": "2025-02-18T12:00:00"
    }
  ],
  "hasMore": false
}
```

### Лента (сообщения + события)

```http
GET /api/rooms/{roomId}/feed
Authorization: Bearer <token>
```

---

## 6. WebSocket — real-time

### Подключение к чату

**URL:**

```
ws://localhost:8000/api/rooms/{roomId}/chat?token={JWT}
```

Замените `localhost:8000` на ваш хост. В production: `wss://`.

**Важно:** подключите WebSocket **до** отправки сообщений. Иначе broadcast не дойдёт.

### Входящие сообщения

Все сообщения имеют вид:

```json
{
  "type": "connected" | "message" | "event" | "pong" | "error",
  "payload": { ... }
}
```

| type | Описание |
|------|----------|
| connected | Подключение успешно |
| message | Новое сообщение (в т.ч. от агентов) |
| event | Системное событие |
| pong | Ответ на ping |
| error | Ошибка |

**Структура `payload` для `message`:**

```json
{
  "id": "124",
  "text": "Предлагаю начать с исследования ЦА...",
  "sender": "Маркетолог",
  "agentId": "1",
  "timestamp": "2025-02-18T12:00:05"
}
```

- `agentId: null` — сообщение пользователя  
- `sender: "Система"` — финальный синтезированный ответ (в режимах оркестрации)

### Ping/Pong

Клиент должен отправлять ping раз в 20–30 секунд:

```json
{"type": "ping"}
```

Сервер отвечает `{"type": "pong", "payload": {}}`.

### Пример (JavaScript)

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
    // Добавить в UI
  }
};

ws.onopen = () => {
  setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 25000);
};
```

---

## 7. Граф отношений

### WebSocket графа

```
ws://localhost:8000/api/rooms/{roomId}/graph?token={JWT}
```

**Входящие:**

- `connected` — подключение
- `edge_update` — обновление ребра между агентами
- `pong` — ответ на ping
- `error` — ошибка

**Пример `edge_update`:**

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

### REST: граф и отношения

```http
GET /api/rooms/{roomId}/relationship-model
GET /api/rooms/{roomId}/relationships
Authorization: Bearer <token>
```

---

## 8. Режимы оркестрации

| Режим | Поведение |
|-------|-----------|
| **single** | Каждый агент отвечает отдельно. При `POST /messages` — каждый агент генерирует свой ответ. При `POST /agents/{id}/messages` — только этот агент. |
| **circular** | Агенты по кругу (до 5 раундов), фокус на запросе пользователя. Финальный ответ формирует SolutionSynthesizer. |
| **narrator** | Первый агент — рассказчик, остальные — персонажи. История развивается по сюжету. |
| **full_context** | Обсуждение с суммаризацией раундов. |

### Pipeline (при orchestration_type ≠ single)

Каждый запрос проходит этапы:

1. RETRIEVE_MEMORY — загрузка контекста из ChromaDB  
2. PLAN — план (запрос пользователя)  
3. DISCUSS — обсуждение агентов  
4. SYNTHESIZE — финальный ответ (SolutionSynthesizer)  
5. STORE_MEMORY — сохранение в память  
6. FACT_EXTRACTION — извлечение триплетов  
7. UPDATE_GRAPH — обновление графа  

Сообщения агентов и финальный ответ приходят по WebSocket по мере выполнения.

---

## 9. Пример полной интеграции

### JavaScript / TypeScript

```javascript
const API = "http://localhost:8000";
const WS = "ws://localhost:8000";

// 1. Авторизация
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

// 2. Комната
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

// 3. Агент
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

// 4. WebSocket чата
function connectChat(roomId, token, onMessage) {
  const ws = new WebSocket(`${WS}/api/rooms/${roomId}/chat?token=${token}`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "message") onMessage(data.payload);
    if (data.type === "connected") console.log("Connected");
  };
  ws.onopen = () => {
    setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 25000);
  };
  return ws;
}

// 5. Отправка сообщения
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

// Полный flow
(async () => {
  const token = await login("user@example.com", "password123");
  const room = await createRoom(token, "Моя комната", "circular");
  const roomId = room.id;

  await addAgent(token, roomId, "Аналитик", "Любит цифры и факты.");
  await addAgent(token, roomId, "Креативщик", "Генерирует идеи.");

  const ws = connectChat(roomId, token, (msg) => {
    console.log(`${msg.sender}: ${msg.text}`);
  });

  // Ждём подключения, затем отправляем
  await new Promise((r) => setTimeout(r, 1000));
  await sendMessage(token, roomId, "Придумайте название для приложения доставки еды.");

  // Ответы агентов придут по ws
})();
```

### React (кратко)

```tsx
// Хук WebSocket
useEffect(() => {
  if (!roomId || !token) return;
  const ws = new WebSocket(`ws://localhost:8000/api/rooms/${roomId}/chat?token=${token}`);
  ws.onmessage = (e) => {
    const { type, payload } = JSON.parse(e.data);
    if (type === "message") setMessages((m) => [...m, payload]);
  };
  return () => ws.close();
}, [roomId, token]);
```

---

## 10. Устранение неполадок

### Агенты не отвечают

- Проверьте, что WebSocket **подключён до** отправки сообщения
- Убедитесь, что в комнате есть агенты
- Для orchestration: проверьте `YANDEX_CLOUD_FOLDER` и `YANDEX_CLOUD_API_KEY`

### 401 Unauthorized

- Токен не передан или истёк
- Добавьте `Authorization: Bearer <token>`

### 403 Forbidden (WebSocket)

- Пользователь не имеет доступа к комнате (комната принадлежит другому user_id)

### Оркестрация не запускается

- Проверьте `orchestration_type` комнаты (не `single`)
- В логах: `create_pipeline_components YandexAgentClient fail` — нет Yandex ключей

### Сообщения приходят с задержкой

- Pipeline выполняет несколько этапов (memory, discuss, synthesize). Это нормально.
- В режиме circular — до 5 раундов обсуждения + синтез.

### CORS

По умолчанию FastAPI разрешает запросы с любого origin. Для production настройте CORS в `app/main.py`.

---

## Краткая справка эндпоинтов

| Метод | Путь | Auth |
|-------|------|------|
| POST | /api/auth/register | — |
| POST | /api/auth/login | — |
| GET | /api/auth/me | Bearer |
| GET | /api/rooms | Bearer |
| POST | /api/rooms | Bearer |
| GET | /api/rooms/{id} | Bearer |
| PATCH | /api/rooms/{id} | Bearer |
| DELETE | /api/rooms/{id} | Bearer |
| GET | /api/rooms/{id}/agents | Bearer |
| POST | /api/rooms/{id}/agents | Bearer |
| POST | /api/rooms/{id}/messages | Bearer |
| GET | /api/rooms/{id}/messages | Bearer |
| GET | /api/rooms/{id}/feed | Bearer |
| POST | /api/rooms/{id}/agents/{aid}/messages | Bearer |
| GET | /api/rooms/{id}/relationship-model | Bearer |
| GET | /api/default-agents | — |
| WS | /api/rooms/{id}/chat?token= | JWT в query |
| WS | /api/rooms/{id}/graph?token= | JWT в query |
