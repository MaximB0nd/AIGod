/**
 * API комнат
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'
import type { Room } from '@/types/room'

export interface CreateRoomRequest {
  name: string
  description?: string
  orchestration_type?: 'single' | 'circular' | 'narrator' | 'full_context'
}

/** PATCH /api/rooms/{roomId} — только description и speed (0.1–10.0) */
export interface UpdateRoomRequest {
  description?: string
  speed?: number
}

export interface RoomsListResponse {
  rooms: Room[]
}

/**
 * POST /api/rooms — создать комнату
 * description опционально (API: "string (опционально)")
 */
export async function createRoom(data: CreateRoomRequest): Promise<Room> {
  const body: Record<string, string> = { name: data.name }
  if (data.description != null && data.description.trim() !== '') {
    body.description = data.description.trim()
  }
  if (data.orchestration_type != null) {
    body.orchestration_type = data.orchestration_type
  }
  return apiFetch<Room>('/api/rooms', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/**
 * GET /api/rooms — список комнат пользователя
 */
export async function fetchRooms(): Promise<Room[]> {
  const res = await apiFetch<RoomsListResponse>('/api/rooms')
  return res.rooms ?? []
}

/**
 * GET /api/rooms/{roomId} — информация о комнате
 */
export async function fetchRoom(roomId: string): Promise<Room | null> {
  try {
    return await apiFetch<Room>(`/api/rooms/${roomId}`)
  } catch {
    return null
  }
}

/**
 * PATCH /api/rooms/{roomId} — обновить комнату
 */
export async function updateRoom(
  roomId: string,
  data: UpdateRoomRequest
): Promise<Room> {
  return apiFetch<Room>(`/api/rooms/${roomId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * DELETE /api/rooms/{roomId} — удалить комнату
 */
export async function deleteRoom(roomId: string): Promise<void> {
  await apiFetch(`/api/rooms/${roomId}`, { method: 'DELETE' })
}
