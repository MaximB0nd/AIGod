/**
 * Типы для агентов (по BACKEND_API_REQUIREMENTS.md)
 */

export interface Mood {
  mood: string
  level: number
  icon?: string
  color?: string
}

export interface AgentSummary {
  id: string
  name: string
  avatar?: string
  mood: Mood
}

export interface Memory {
  id: string
  content: string
  timestamp: string
  importance?: number
}

export interface Plan {
  id: string
  description: string
  status: 'pending' | 'in_progress' | 'done'
}

export interface Agent extends AgentSummary {
  character: string
  keyMemories?: Memory[]
  plans?: Plan[]
}

export interface CreateAgentRequest {
  name: string
  character: string
  avatar?: string
}
