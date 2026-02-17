/**
 * API симуляции (старт/стоп эмуляции, скорость времени)
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'

/**
 * POST /api/rooms/{roomId}/emulation/start — включить эмуляцию
 */
export async function startEmulation(roomId: string): Promise<{ running?: boolean } | void> {
  return apiFetch<{ running?: boolean } | void>(`/api/rooms/${roomId}/emulation/start`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/**
 * POST /api/rooms/{roomId}/emulation/stop — выключить эмуляцию
 */
export async function stopEmulation(roomId: string): Promise<{ running?: boolean } | void> {
  return apiFetch<{ running?: boolean } | void>(`/api/rooms/${roomId}/emulation/stop`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
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
