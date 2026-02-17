# Подключение фронтенда к AIgod API

Краткое руководство по подключению клиента к бэкенду.

---

## Базовые URL

| Режим | REST | WebSocket |
|-------|------|-----------|
| Локально | `http://localhost:8000` | `ws://localhost:8000` |
| Production | `https://your-domain.com` | `wss://your-domain.com` |

Swagger: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## 1. Авторизация

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
Ответ: `{ "token": "eyJ...", "id", "email", "username" }`

### Логин
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```
Ответ: `{ "token": "eyJ...", ... }`

### Использование токена
Добавить заголовок ко всем защищённым запросам:
```
Authorization: Bearer <token>
```

---

## 2. Эндпоинты без авторизации

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/login | Логин |
| GET | /api/agents | Каталог агентов (пусто при первом запуске) |
| GET | /api/default-agents | Шаблоны агентов |
| GET | /api/default-agents/{id} | Шаблон для предзаполнения формы |
| GET | /api/prompts/system | Системные промпты |
| GET | /api/prompts/templates | Шаблоны промптов |
| POST | /api/prompts/build | Сборка промпта |

---

## 3. Типичный сценарий

### Создание комнаты и добавление агента
1. `POST /api/auth/login` → сохранить `token`
2. `POST /api/rooms` с `{ "name": "Моя комната", "orchestration_type": "single" }` → получить `roomId`
3. `GET /api/default-agents` → список шаблонов
4. `GET /api/default-agents/1` → `{ name, character, avatar }` для формы
5. `POST /api/rooms/{roomId}/agents` с `{ name, character, avatar }` → агент добавлен

### Чат и WebSocket

**Важно:** WebSocket нужно подключать до отправки сообщений. Иначе клиент не получит broadcast.

1. **При открытии чата:** подключиться к `ws://localhost:8000/api/rooms/{roomId}/chat?token=<token>`
2. **Загрузить историю:** `GET /api/rooms/{roomId}/messages` или `GET /api/rooms/{roomId}/feed`
3. **Отправить сообщение:** `POST /api/rooms/{roomId}/agents/{agentId}/messages` с `{ "text": "Привет", "sender": "user" }`

Если в комнате несколько агентов — укажите `agentId` того, кому адресовано сообщение (например, первого из `GET /api/rooms/{roomId}/agents`).

---

## 4. WebSocket

### Чат
```
ws://localhost:8000/api/rooms/{roomId}/chat?token={JWT}
```
Входящие: `connected`, `message`, `event`, `pong`, `error`.  
Клиент отправляет `{"type": "ping"}` раз в 20–30 сек.

### Граф отношений
```
ws://localhost:8000/api/rooms/{roomId}/graph?token={JWT}
```
Входящие: `connected`, `edge_update`, `pong`, `error`.

Подробнее: `WEBSOCKET_CLIENT.md`.

---

## 5. CORS

По умолчанию FastAPI разрешает запросы с любого origin. Для production настрой CORS в `app/main.py` при необходимости.

---

## 6. Пример (JavaScript)

```javascript
const API = 'http://localhost:8000';
const token = (await fetch(`${API}/api/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com', password: 'password123' })
}).then(r => r.json())).token;

// Запрос с авторизацией
const rooms = await fetch(`${API}/api/rooms`, {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());
```
