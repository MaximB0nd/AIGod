/**
 * Типы для агентов (API /api/rooms/{roomId}/agents, relationships)
 * @see API_DOCS.md v1.0.0
 */

export interface AgentMood {
  mood: string
  level: number
  icon?: string
  color?: string
}

export interface AgentSummary {
  id: string
  name: string
  avatar?: string
  mood?: AgentMood
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

/** Взаимоотношение с другим агентом (из agent.relationships) */
export interface AgentRelationship {
  agentId?: string
  agentName?: string
  sympathyLevel?: number
}

export interface Agent extends AgentSummary {
  character?: string
  /** Ключевые воспоминания (всегда массив, может быть пустым) */
  keyMemories?: Memory[]
  /** Планы (всегда массив, может быть пустым) */
  plans?: Plan[]
  /** Взаимоотношения с другими агентами (всегда массив, может быть пустым) */
  relationships?: AgentRelationship[]
}

export interface RelationshipsResponse {
  nodes: Array<{
    id: string
    name: string
    avatar?: string
    mood?: { mood?: string; level?: number; color?: string }
  }>
  edges: Array<{
    from: string
    to: string
    agentName?: string
    sympathyLevel: number
  }>
}
