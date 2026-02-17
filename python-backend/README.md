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

### Устранение неполадок: чат пустой

Если сообщения сохраняются в БД, но не отображаются, см. раздел «Устранение неполадок» в **WEBSOCKET_CLIENT.md**. Основная причина — WebSocket не подключён до отправки сообщения.
