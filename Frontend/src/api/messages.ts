/**
 * API сообщений
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'

export interface SendMessageRequest {
  text: string
  sender: 'user'
}

export interface MessageResponse {
  id: string
  text: string
  sender: 'user' | 'agent'
  timestamp: string
  agentResponse?: string
}

/**
 * POST /api/rooms/{roomId}/agents/{agentId}/messages — отправить сообщение агенту
 */
export async function sendMessage(
  roomId: string,
  agentId: string,
  data: SendMessageRequest
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    `/api/rooms/${roomId}/agents/${agentId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ ...data, sender: 'user' }),
    }
  )
}
