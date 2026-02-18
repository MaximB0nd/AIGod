/**
 * API статистики использования Yandex API
 * @see API_DOCS.md v1.0.0
 */

import { apiFetch } from './client'

export interface UsageResponse {
  today: string
  callCount: number
  limitPerDay: number | null
  remaining: number
  limitExceeded: boolean
}

/**
 * GET /api/usage — статистика обращений к Yandex API (защита от перерасхода)
 * Без авторизации.
 */
export async function fetchUsage(): Promise<UsageResponse> {
  return apiFetch<UsageResponse>('/api/usage', { skipAuth: true })
}
