/**
 * API для комнат (групп)
 * Заготовки — готовы к подключению бэкенда
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import type { Room } from '@/types/room'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

/**
 * Получить информацию по комнате
 * GET /api/rooms/{roomId}
 * @param fallback — для мока: данные из чата (убрать после подключения бэкенда)
 */
export async function fetchRoom(
  roomId: string,
  fallback?: { name?: string; agentCount?: number }
): Promise<Room | null> {
  // TODO: подключить бэкенд
  // const res = await fetch(`${API_BASE}/rooms/${roomId}`, {
  //   headers: { Authorization: `Bearer ${token}` },
  // })
  // if (!res.ok) return null
  // return res.json()

  // Мок для разработки
  return Promise.resolve({
    id: roomId,
    name: fallback?.name ?? 'Комната',
    description: 'Описание группы появится после подключения бэкенда.',
    speed: 1.0,
    createdAt: new Date().toISOString(),
    agentCount: fallback?.agentCount ?? 0,
  })
}

/**
 * Обновить информацию о комнате
 * PATCH /api/rooms/{roomId}
 */
export async function updateRoom(
  roomId: string,
  data: { name?: string; description?: string; speed?: number }
): Promise<Room | null> {
  // TODO: подключить бэкенд
  // const res = await fetch(`${API_BASE}/rooms/${roomId}`, {
  //   method: 'PATCH',
  //   headers: {
  //     'Content-Type': 'application/json',
  //     Authorization: `Bearer ${token}`,
  //   },
  //   body: JSON.stringify(data),
  // })
  // if (!res.ok) return null
  // return res.json()

  return Promise.resolve(null)
}
