/**
 * Типы для ленты и событий (по BACKEND_API_REQUIREMENTS.md)
 */

export interface FeedEvent {
  id: string
  type: string
  agentIds: string[]
  description: string
  timestamp: string
  moodImpact?: Record<string, number>
}

export interface FeedMessage {
  id: string
  text: string
  sender: 'user' | 'agent'
  agentId?: string | null
  timestamp: string
}

export type FeedItemPayload = FeedEvent | FeedMessage

export interface FeedResponse {
  items: Array<
    | { type: 'event'; id: string; eventType: string; agentIds: string[]; description: string; timestamp: string }
    | { type: 'message'; id: string; text: string; sender: 'user' | 'agent'; agentId: string | null; timestamp: string }
  >
}
