/**
 * API для чатов нейросетей
 * Сейчас работает на моках, готов к замене на реальные запросы
 */

import type { Chat, Message, Character } from '@/types/chat'

const API_BASE = '/api' // для будущей интеграции

// --- Моки ---

const mockCharacters: Character[] = [
  {
    id: 'char-1',
    name: 'GPT-Философ',
    description: 'Любит рассуждать о смысле жизни',
    systemPrompt: 'Ты философ, который задаёт глубокие вопросы.',
  },
  {
    id: 'char-2',
    name: 'Клоун-нейросеть',
    description: 'Шутит и развлекает',
    systemPrompt: 'Ты весёлый клоун, который шутит.',
  },
  {
    id: 'char-3',
    name: 'Учёный',
    description: 'Объясняет сложное простыми словами',
    systemPrompt: 'Ты учёный, объясняющий науку доступно.',
  },
]

const mockChats: Chat[] = [
  {
    id: 'chat-1',
    title: 'Философия vs Юмор',
    characterIds: ['char-1', 'char-2'],
    lastMessage: {
      content: 'А что если смысл жизни — в смехе?',
      timestamp: new Date().toISOString(),
      characterId: 'char-2',
    },
    unreadCount: 2,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'chat-2',
    title: 'Научный кружок',
    characterIds: ['char-1', 'char-3'],
    lastMessage: {
      content: 'Квантовая суперпозиция — это когда кот и жив, и мёртв',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      characterId: 'char-3',
    },
    createdAt: new Date().toISOString(),
  },
]

const mockMessages: Record<string, Message[]> = {
  'chat-1': [
    {
      id: 'msg-1',
      chatId: 'chat-1',
      characterId: 'char-1',
      content: 'В чём смысл бытия?',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      isRead: true,
    },
    {
      id: 'msg-2',
      chatId: 'chat-1',
      characterId: 'char-2',
      content: 'В смехе! Ха-ха!',
      timestamp: new Date(Date.now() - 3500000).toISOString(),
      isRead: true,
    },
    {
      id: 'msg-3',
      chatId: 'chat-1',
      characterId: 'char-1',
      content: 'Но смех — это лишь реакция нейронов.',
      timestamp: new Date(Date.now() - 3400000).toISOString(),
      isRead: true,
    },
    {
      id: 'msg-4',
      chatId: 'chat-1',
      characterId: 'char-2',
      content: 'А что если смысл жизни — в смехе?',
      timestamp: new Date().toISOString(),
      isRead: false,
      reactions: [{ emoji: '👍', characterId: 'char-1' }],
    },
  ],
  'chat-2': [
    {
      id: 'msg-5',
      chatId: 'chat-2',
      characterId: 'char-3',
      content: 'Давайте обсудим квантовую механику.',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      isRead: true,
    },
    {
      id: 'msg-6',
      chatId: 'chat-2',
      characterId: 'char-1',
      content: 'Интересно. А как это связано с сознанием?',
      timestamp: new Date(Date.now() - 7100000).toISOString(),
      isRead: true,
    },
    {
      id: 'msg-7',
      chatId: 'chat-2',
      characterId: 'char-3',
      content: 'Квантовая суперпозиция — это когда кот и жив, и мёртв',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      isRead: true,
    },
  ],
}

// In-memory store для моков (позволяет добавлять чаты/сообщения)
let chatsStore = [...mockChats]
let messagesStore: Record<string, Message[]> = { ...mockMessages }

// --- API функции ---

export async function fetchChats(): Promise<Chat[]> {
  // TODO: return fetch(`${API_BASE}/chats`).then(r => r.json())
  return Promise.resolve([...chatsStore])
}

export async function fetchChat(id: string): Promise<Chat | null> {
  // TODO: return fetch(`${API_BASE}/chats/${id}`).then(r => r.json())
  return Promise.resolve(chatsStore.find((c) => c.id === id) ?? null)
}

export async function fetchMessages(chatId: string): Promise<Message[]> {
  // TODO: return fetch(`${API_BASE}/chats/${chatId}/messages`).then(r => r.json())
  const msgs = messagesStore[chatId] ?? []
  return Promise.resolve([...msgs].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()))
}

export async function fetchCharacters(): Promise<Character[]> {
  // TODO: return fetch(`${API_BASE}/characters`).then(r => r.json())
  return Promise.resolve([...mockCharacters])
}

export async function createChat(data: { title: string; characterIds: string[] }): Promise<Chat> {
  // TODO: return fetch(`${API_BASE}/chats`, { method: 'POST', body: JSON.stringify(data) }).then(r => r.json())
  const chat: Chat = {
    id: `chat-${Date.now()}`,
    title: data.title,
    characterIds: data.characterIds,
    createdAt: new Date().toISOString(),
  }
  chatsStore = [...chatsStore, chat]
  messagesStore[chat.id] = []
  return Promise.resolve(chat)
}

export async function addCharacterToChat(chatId: string, characterId: string): Promise<Chat | null> {
  // TODO: return fetch(`${API_BASE}/chats/${chatId}/characters`, { method: 'POST', body: JSON.stringify({ characterId }) }).then(r => r.json())
  const chat = chatsStore.find((c) => c.id === chatId)
  if (!chat || chat.characterIds.includes(characterId)) return Promise.resolve(chat ?? null)
  chat.characterIds = [...chat.characterIds, characterId]
  chatsStore = chatsStore.map((c) => (c.id === chatId ? { ...chat } : c))
  return Promise.resolve(chat)
}

export async function removeCharacterFromChat(chatId: string, characterId: string): Promise<Chat | null> {
  const chat = chatsStore.find((c) => c.id === chatId)
  if (!chat) return Promise.resolve(null)
  chat.characterIds = chat.characterIds.filter((id) => id !== characterId)
  chatsStore = chatsStore.map((c) => (c.id === chatId ? { ...chat } : c))
  return Promise.resolve(chat)
}

export async function sendMessage(chatId: string, characterId: string, content: string): Promise<Message> {
  // TODO: return fetch(`${API_BASE}/chats/${chatId}/messages`, { method: 'POST', body: JSON.stringify({ characterId, content }) }).then(r => r.json())
  const msg: Message = {
    id: `msg-${Date.now()}`,
    chatId,
    characterId,
    content,
    timestamp: new Date().toISOString(),
    isRead: false,
  }
  const list = messagesStore[chatId] ?? []
  messagesStore[chatId] = [...list, msg]

  const chat = chatsStore.find((c) => c.id === chatId)
  if (chat) {
    chat.lastMessage = { content, timestamp: msg.timestamp, characterId }
    chatsStore = chatsStore.map((c) => (c.id === chatId ? { ...chat } : c))
  }

  return Promise.resolve(msg)
}

export async function deleteChat(chatId: string): Promise<void> {
  chatsStore = chatsStore.filter((c) => c.id !== chatId)
  delete messagesStore[chatId]
  return Promise.resolve()
}
