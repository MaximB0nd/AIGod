# Архитектура проекта — Чаты нейросетей

## Обзор

Приложение имитирует интерфейс Telegram для чатов, в которых общаются персонажи-нейросети. Двухпанельный макет: слева список чатов, справа — активный чат с историей.

## Структура проекта

```
src/
├── api/                    # API-слой
│   ├── chat.ts             # API чатов (моки, готов к замене на fetch)
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

Все вызовы в `src/api/chat.ts` сейчас возвращают моки. Для перехода на реальный API:

1. Замените `Promise.resolve(...)` на `fetch(\`${API_BASE}/...\`)`.
2. Установите `API_BASE` (например, `import.meta.env.VITE_API_URL`).
3. Добавьте обработку ошибок и загрузки.

Пример:

```ts
export async function fetchChats(): Promise<Chat[]> {
  const res = await fetch(`${API_BASE}/chats`)
  if (!res.ok) throw new Error('Failed to fetch chats')
  return res.json()
}
```

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
