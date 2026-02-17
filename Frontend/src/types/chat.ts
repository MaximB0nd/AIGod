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
}

export interface Message {
  id: string
  chatId: string
  characterId: string
  content: string
  timestamp: string
  isRead: boolean
  sender?: 'user' | 'agent' | 'system'
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
  | { type: 'message'; data: Message & { sender?: 'user' | 'agent' | 'system' } }
  | { type: 'event'; data: Event }
