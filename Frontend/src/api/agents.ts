/**
 * API агентов и отношений
 * @see API_DOCS.md v1.0.0
 */

import { apiFetch } from './client'
import type { Agent, Memory, Plan, RelationshipsResponse } from '@/types/agent'

export type { RelationshipsResponse }

export interface AgentSummary {
  id: string
  name: string
  avatar?: string
  mood?: { mood: string; level: number; icon?: string; color?: string }
}

export interface AgentsResponse {
  agents: AgentSummary[]
}

/**
 * GET /api/rooms/{roomId}/agents — все агенты комнаты
 */
export async function fetchAgents(roomId: string): Promise<AgentSummary[]> {
  const res = await apiFetch<AgentsResponse>(`/api/rooms/${roomId}/agents`)
  return res.agents ?? []
}

export interface CreateAgentRequest {
  name: string
  character?: string
  avatar?: string
  agentId?: number
}

/**
 * POST /api/rooms/{roomId}/agents — создать или добавить агента
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
 * DELETE /api/rooms/{roomId}/agents/{agentId} — удалить агента из комнаты
 */
export async function deleteAgent(
  roomId: string,
  agentId: string
): Promise<void> {
  return apiFetch(`/api/rooms/${roomId}/agents/${agentId}`, {
    method: 'DELETE',
  })
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId} — полная информация по агенту
 */
export async function fetchAgent(roomId: string, agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/rooms/${roomId}/agents/${agentId}`)
}

export interface MemoriesResponse {
  memories: Memory[]
  total: number
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId}/memories — воспоминания агента
 */
export async function fetchAgentMemories(
  roomId: string,
  agentId: string,
  params?: { limit?: number; offset?: number }
): Promise<MemoriesResponse> {
  const search = new URLSearchParams()
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const q = search.toString() ? `?${search}` : ''
  return apiFetch<MemoriesResponse>(`/api/rooms/${roomId}/agents/${agentId}/memories${q}`)
}

export interface PlansResponse {
  plans: Plan[]
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId}/plans — планы агента
 */
export async function fetchAgentPlans(
  roomId: string,
  agentId: string
): Promise<PlansResponse> {
  return apiFetch<PlansResponse>(`/api/rooms/${roomId}/agents/${agentId}/plans`)
}

/**
 * GET /api/rooms/{roomId}/relationships — граф отношений
 */
export async function fetchRelationships(
  roomId: string
): Promise<RelationshipsResponse> {
  return apiFetch<RelationshipsResponse>(`/api/rooms/${roomId}/relationships`)
}
