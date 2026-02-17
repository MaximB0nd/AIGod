/**
 * Типы данных для AIgod
 * Соответствуют контракту API (API_DOCS.md v1.0.0)
 */

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
export * from './auth'
export * from './agent'
export * from './room'
