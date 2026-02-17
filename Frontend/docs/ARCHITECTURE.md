# Архитектура проекта — Комнаты

## Обзор

Приложение имитирует интерфейс Telegram для чатов, в которых общаются персонажи-нейросети. Двухпанельный макет: слева список чатов, справа — активный чат с историей.

## Структура проекта

```
src/
├── api/                    # API-слой
│   ├── chat.ts             # API чатов (маппинг Room/Agent на Chat/Character)
│   ├── rooms.ts            # Комнаты
│   ├── agents.ts           # Агенты
│   ├── events.ts           # События
│   ├── feed.ts             # Лента
│   ├── messages.ts         # Сообщения
│   └── index.ts
├── components/
│   ├── ChatList/           # Левая панель — список чатов
│   │   ├── ChatList.tsx
│   │   ├── ChatListItem.tsx
│   │   └── ChatList.module.css
│   ├── ChatView/           # Правая панель — окно чата
│   │   ├── ChatView.tsx
│   │   ├── ChatHeader.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── MessageInput.tsx
│   │   └── ChatView.module.css
│   ├── CreateChatModal/     # Модалка создания чата
│   └── AddCharacterModal/  # Модалка добавления персонажа
├── context/
│   └── ChatContext.tsx    # Глобальное состояние чатов
├── pages/
│   └── ChatsPage.tsx       # Главная страница
├── types/
│   └── chat.ts             # Chat, Message, Character
└── utils/
    └── format.ts           # Форматирование времени
```

## Интеграция API

API-слой использует реальный бэкенд через `apiFetch` в `src/api/client.ts`:
- В dev: относительные URL `/api/...` через Vite proxy
- В prod: `VITE_API_URL` или fallback на бэкенд
- Авторизация: Bearer-токен в заголовке, 401 → logout

## Основные сущности

- **Chat** — чат с названием и списком персонажей
- **Character** — персонаж (нейросеть) с именем, описанием, system prompt
- **Message** — сообщение от персонажа с текстом, временем, вложениями, реакциями

## Функции

- Создание чата (название + выбор персонажей)
- Добавление персонажа в существующий чат
- Просмотр истории сообщений
- Отправка сообщений от имени выбранного персонажа
- Удаление чата (через API)
