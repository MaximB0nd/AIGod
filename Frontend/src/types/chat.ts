/**
 * Типы для чата (Room → Chat, Agent → Character)
 * @see API_DOCS.md v1.0.0
 */

export interface Chat {
  id: string
  title: string
  characterIds: string[]
  avatar?: string
  createdAt: string
  /** Режим оркестрации: single | circular | narrator | full_context */
  orchestration_type?: string
  lastMessage?: { content: string; timestamp: string }
  unreadCount?: number
}

/** sender: 'user' — от пользователя; строка — имя агента или спецтип (🎭 Рассказчик, 📊 Суммаризатор, Система) */
export interface Message {
  id: string
  chatId: string
  characterId: string
  content: string
  timestamp: string
  isRead: boolean
  sender?: 'user' | 'agent' | 'system' | string
}

export interface Character {
  id: string
  name: string
  avatar?: string
  description?: string
}

export interface Event {
  id: string
  chatId: string
  type: string
  description: string
  agentIds: string[]
  timestamp: string
}

export type FeedItem =
  | { type: 'message'; data: Message & { sender?: 'user' | 'agent' | 'system' | string } }
  | { type: 'event'; data: Event }
