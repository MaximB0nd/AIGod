/**
 * API агентов (в контексте комнаты)
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'
import type { Agent, AgentSummary, CreateAgentRequest, Memory, Plan } from '@/types/agent'

export interface AgentsListResponse {
  agents: AgentSummary[]
}

export interface MemoriesResponse {
  memories: Memory[]
  total: number
}

export interface PlansResponse {
  plans: Plan[]
}

export interface RelationshipsResponse {
  nodes: Array<{
    id: string
    name: string
    avatar?: string
    mood: { mood: string; level: number; color?: string }
  }>
  edges: Array<{ from: string; to: string; sympathyLevel: number }>
}

/**
 * GET /api/rooms/{roomId}/agents — список агентов комнаты
 */
export async function fetchAgents(roomId: string): Promise<AgentSummary[]> {
  const res = await apiFetch<AgentsListResponse>(`/api/rooms/${roomId}/agents`)
  return res.agents ?? []
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId} — полная информация об агенте
 */
export async function fetchAgent(roomId: string, agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/rooms/${roomId}/agents/${agentId}`)
}

/**
 * POST /api/rooms/{roomId}/agents — создать агента
 */
export async function createAgent(
  roomId: string,
  data: CreateAgentRequest
): Promise<AgentSummary> {
  return apiFetch<AgentSummary>(`/api/rooms/${roomId}/agents`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * DELETE /api/rooms/{roomId}/agents/{agentId} — удалить агента
 */
export async function deleteAgent(roomId: string, agentId: string): Promise<void> {
  await apiFetch(`/api/rooms/${roomId}/agents/${agentId}`, { method: 'DELETE' })
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId}/memories — воспоминания агента
 */
export async function fetchAgentMemories(
  roomId: string,
  agentId: string,
  params?: { limit?: number; offset?: number }
): Promise<MemoriesResponse> {
  const q = new URLSearchParams()
  if (params?.limit != null) q.set('limit', String(params.limit))
  if (params?.offset != null) q.set('offset', String(params.offset))
  const query = q.toString()
  return apiFetch<MemoriesResponse>(
    `/api/rooms/${roomId}/agents/${agentId}/memories${query ? `?${query}` : ''}`
  )
}

/**
 * GET /api/rooms/{roomId}/relationships — граф отношений
 */
export async function fetchRelationships(roomId: string): Promise<RelationshipsResponse> {
  return apiFetch<RelationshipsResponse>(`/api/rooms/${roomId}/relationships`)
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId}/plans — планы агента
 */
export async function fetchAgentPlans(
  roomId: string,
  agentId: string
): Promise<Plan[]> {
  const res = await apiFetch<PlansResponse>(
    `/api/rooms/${roomId}/agents/${agentId}/plans`
  )
  return res.plans ?? []
}
