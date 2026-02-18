/**
 * API событий
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'

export interface CreateEventRequest {
  description: string
  type: string
  agentIds?: string[]
}

export interface EventResponse {
  id: string
  type: string
  agentIds: string[]
  description: string
  timestamp: string
}

/**
 * POST /api/rooms/{roomId}/events — создать событие
 */
export async function createEvent(
  roomId: string,
  data: CreateEventRequest
): Promise<EventResponse> {
  return apiFetch<EventResponse>(`/api/rooms/${roomId}/events`, {
    method: 'POST',
    body: JSON.stringify({
      description: data.description,
      type: data.type ?? 'user_event',
      agentIds: data.agentIds ?? [],
    }),
  })
}

/**
 * POST /api/rooms/{roomId}/events/broadcast — событие всем агентам
 */
export async function broadcastEvent(
  roomId: string,
  data: { description: string; type?: string }
): Promise<EventResponse> {
  return apiFetch<EventResponse>(`/api/rooms/${roomId}/events/broadcast`, {
    method: 'POST',
    body: JSON.stringify({
      description: data.description,
      type: data.type ?? 'user_event',
    }),
  })
}
