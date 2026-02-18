/**
 * API сообщений
 * @see API_DOCS.md v1.0.0
 */

import { apiFetch } from './client'

export interface SendMessageResponse {
  id: string
  text: string
  sender: 'user' | 'agent'
  timestamp: string
  agentId: string | null
  agentResponse: string | null
}

/**
 * POST /api/rooms/{roomId}/messages — отправить сообщение в общий чат комнаты (всем агентам)
 */
export async function sendMessageToRoom(
  roomId: string,
  data: { text: string; sender: 'user' }
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(`/api/rooms/${roomId}/messages`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * POST /api/rooms/{roomId}/agents/{agentId}/messages — отправить сообщение конкретному агенту
 */
export async function sendMessage(
  roomId: string,
  agentId: string,
  data: { text: string; sender: 'user' }
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(
    `/api/rooms/${roomId}/agents/${agentId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}

/** sender может быть именем агента или спецтипом: 🎭 Рассказчик, 📊 Суммаризатор, Система */
export interface MessagesResponse {
  messages: Array<{
    id: string
    text: string
    sender: 'user' | 'agent' | 'system' | string
    agentId: string | null
    timestamp: string
  }>
  hasMore: boolean
}

/**
 * GET /api/rooms/{roomId}/messages — сообщения для ленивой загрузки
 * @param roomId — ID комнаты
 * @param params.after_id — загрузить сообщения старше этого id (id < after_id)
 * @param params.limit — кол-во сообщений (1–100)
 */
export async function fetchMessages(
  roomId: string,
  params?: { after_id?: number; limit?: number }
): Promise<MessagesResponse> {
  const search = new URLSearchParams()
  if (params?.after_id != null) search.set('after_id', String(params.after_id))
  if (params?.limit != null) search.set('limit', String(params.limit))
  const q = search.toString() ? `?${search}` : ''
  return apiFetch<MessagesResponse>(`/api/rooms/${roomId}/messages${q}`)
}
