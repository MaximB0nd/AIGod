/**
 * API симуляции (скорость времени)
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'

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
