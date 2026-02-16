/**
 * Типы данных для AIgod
 * Соответствуют контракту API (docs/API_CONTRACT.md)
 */

export interface Memory {
  id: string
  content: string
  importance: number
  timestamp: string
}

export interface Agent {
  id: string
  name: string
  avatar?: string
  personality: string
  mood: 'happy' | 'neutral' | 'sad' | 'angry' | 'excited' | 'anxious'
  memories: Memory[]
  current_goals: string[]
  created_at: string
}

export interface Relationship {
  source_id: string
  target_id: string
  sympathy_level: number
  interaction_count?: number
}

export type TimelineEventType =
  | 'action'
  | 'dialogue'
  | 'thought'
  | 'global_event'
  | 'relationship_change'

export interface TimelineEvent {
  id: string
  type: TimelineEventType
  agent_id?: string
  agent_ids?: string[]
  content: string
  timestamp: string
}

export interface SimulationState {
  time_speed: number
  is_paused: boolean
  current_tick: number
}

export * from './chat'
