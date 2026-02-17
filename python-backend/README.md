# AIgod — Python Backend

API бэкенда для хакатона «Виртуальный мир: симулятор живых существ».

## Быстрый старт

```bash
pip install -r requirements.txt
# Создать .env с YANDEX_CLOUD_FOLDER, YANDEX_CLOUD_API_KEY
uvicorn app.main:app --reload --port 8000
```

Swagger: http://localhost:8000/docs

## Документация

| Файл | Назначение |
|------|-------------|
| **CONNECTION.md** | Подключение фронтенда: auth, URL, сценарии |
| **API_DOCS.md** | Полный справочник REST-эндпоинтов |
| **WEBSOCKET_CLIENT.md** | WebSocket: чат и граф отношений (+ устранение неполадок) |
| **INTEGRATION.md** | Интеграция: LLM, оркестрация, сервисы |

### Архитектура чата

- **`POST /api/rooms/{roomId}/messages`** — сообщение в общий чат комнаты. Ответят все агенты.
- **`POST /api/rooms/{roomId}/agents/{agentId}/messages`** — личная переписка с конкретным агентом.

Для multi-agent UI используйте первый эндпоинт.

### Устранение неполадок: чат пустой

Если сообщения сохраняются в БД, но не отображаются, см. раздел «Устранение неполадок» в **WEBSOCKET_CLIENT.md**.  
Проверьте также: для общего чата комнаты используйте `POST /rooms/{roomId}/messages`, а не `POST /agents/{agentId}/messages`.
