/**
 * API симуляции (оркестрация, скорость времени)
 * @see API_DOCS.md v1.0.0
 */

import { apiFetch } from './client'

/**
 * POST /api/rooms/{roomId}/orchestration/start — запустить оркестрацию
 */
export async function startOrchestration(roomId: string): Promise<{ status?: string; roomId?: number; orchestration_type?: string }> {
  return apiFetch<{ status?: string; roomId?: number; orchestration_type?: string }>(
    `/api/rooms/${roomId}/orchestration/start`,
    { method: 'POST' }
  )
}

/**
 * POST /api/rooms/{roomId}/orchestration/stop — остановить оркестрацию
 */
export async function stopOrchestration(roomId: string): Promise<{ status?: string; roomId?: number }> {
  return apiFetch<{ status?: string; roomId?: number }>(
    `/api/rooms/${roomId}/orchestration/stop`,
    { method: 'POST' }
  )
}

/**
 * PATCH /api/rooms/{roomId}/speed — изменить скорость симуляции
 */
export async function updateRoomSpeed(
  roomId: string,
  speed: number
): Promise<{ speed: number }> {
  return apiFetch<{ speed: number }>(`/api/rooms/${roomId}/speed`, {
    method: 'PATCH',
    body: JSON.stringify({ speed }),
  })
}
