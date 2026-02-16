/**
 * Типы для чатов нейросетей
 */

export interface Character {
  id: string
  name: string
  avatar?: string
  description?: string
  /** Промпт/личность нейросети */
  systemPrompt?: string
}

export interface Message {
  id: string
  chatId: string
  characterId: string
  content: string
  timestamp: string
  isRead?: boolean
  /** Вложения: файлы, изображения */
  attachments?: MessageAttachment[]
  /** Реакции на сообщение */
  reactions?: MessageReaction[]
}

export interface MessageAttachment {
  id: string
  type: 'file' | 'image'
  name: string
  size?: number
  url?: string
}

export interface MessageReaction {
  emoji: string
  characterId: string
}

export interface Chat {
  id: string
  title: string
  avatar?: string
  characterIds: string[]
  lastMessage?: Pick<Message, 'content' | 'timestamp' | 'characterId'>
  unreadCount?: number
  createdAt: string
}
