/**
 * API агентов и графа отношений
 * GET /api/rooms/{roomId}/agents, agents/{id}, relationships
 * PATCH /api/rooms/{roomId}/relationships
 * @see API_DOCS.md, WEBSOCKET_CLIENT.md v1.0.0
 */

import { apiFetch } from './client'
import type { AgentSummary, Agent, RelationshipsResponse } from '@/types/agent'
import type { Memory, Plan } from '@/types/agent'

export type { RelationshipsResponse }

export interface AgentsResponse {
  agents: AgentSummary[]
}

export interface MemoriesResponse {
  memories: Memory[]
  total: number
}

export interface PlansResponse {
  plans: Plan[]
}

export interface CreateAgentRequest {
  name: string
  character?: string
  avatar?: string
  agentId?: number
}

export interface UpdateRelationshipRequest {
  agent1Id: number
  agent2Id: number
  sympathyLevel: number
}

/**
 * GET /api/rooms/{roomId}/agents — все агенты комнаты
 */
export async function fetchAgents(roomId: string): Promise<AgentSummary[]> {
  const res = await apiFetch<AgentsResponse>(`/api/rooms/${roomId}/agents`)
  return res.agents ?? []
}

/**
 * GET /api/rooms/{roomId}/agents/{agentId} — полная информация по агенту
 */
export async function fetchAgent(roomId: string, agentId: string): Promise<Agent> {
  return apiFetch<Agent>(`/api/rooms/${roomId}/agents/${agentId}`)
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
  const qs = search.toString()
  const url = `/api/rooms/${roomId}/agents/${agentId}/memories${qs ? `?${qs}` : ''}`
  return apiFetch<MemoriesResponse>(url)
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
 * GET /api/rooms/{roomId}/relationships — граф отношений (nodes, edges)
 */
export async function fetchRelationships(roomId: string): Promise<RelationshipsResponse> {
  return apiFetch<RelationshipsResponse>(`/api/rooms/${roomId}/relationships`)
}

/**
 * PATCH /api/rooms/{roomId}/relationships — обновить ребро графа
 * Рассылает edge_update в WebSocket графа
 */
export async function updateRelationship(
  roomId: string,
  data: UpdateRelationshipRequest
): Promise<{ from: string; to: string; sympathyLevel: number }> {
  return apiFetch<{ from: string; to: string; sympathyLevel: number }>(
    `/api/rooms/${roomId}/relationships`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )
}

/**
 * POST /api/rooms/{roomId}/agents — создать агента в комнате
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
export async function deleteAgent(roomId: string, agentId: string): Promise<void> {
  await apiFetch(`/api/rooms/${roomId}/agents/${agentId}`, {
    method: 'DELETE',
  })
}

/** Шаблон дефолтного агента (список) — GET /api/default-agents */
export interface DefaultAgentSummary {
  id: number
  name: string
  /** Может быть personality_preview или character в зависимости от бэкенда */
  personality_preview?: string
  character?: string
  avatar_url?: string | null
  avatar?: string | null
}

/** Полный шаблон для создания агента — GET /api/default-agents/{id} */
export interface DefaultAgentTemplate {
  id: number
  name: string
  character: string
  avatar?: string | null
  avatar_url?: string | null
}

/**
 * GET /api/default-agents — список шаблонов для создания агента. Без авторизации.
 * Контракт: массив [{ id, name, personality_preview, avatar_url }]
 */
export async function fetchDefaultAgents(): Promise<DefaultAgentSummary[]> {
  const res = await apiFetch<DefaultAgentSummary[]>(`/api/default-agents`, {
    skipAuth: true,
  })
  return Array.isArray(res) ? res : []
}

/**
 * GET /api/default-agents/{id} — полный шаблон для предзаполнения формы. Без авторизации.
 * Контракт: { id, name, character, avatar }
 */
export async function fetchDefaultAgent(id: number): Promise<DefaultAgentTemplate> {
  return apiFetch<DefaultAgentTemplate>(`/api/default-agents/${id}`, {
    skipAuth: true,
  })
}
