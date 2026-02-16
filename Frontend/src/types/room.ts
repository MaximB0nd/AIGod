/**
 * Типы для комнат (групп) — соответствуют API бэкенда
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

export interface Room {
  id: string
  name: string
  description?: string
  speed?: number
  createdAt: string
  /** Количество агентов в комнате (приходит в GET /api/rooms/{roomId}) */
  agentCount?: number
  /** При PATCH возвращается updatedAt */
  updatedAt?: string
}
