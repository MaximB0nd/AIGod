/**
 * API ленты (сообщения + события)
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'
import type { FeedResponse } from '@/types/feed'

/**
 * GET /api/rooms/{roomId}/feed — последние сообщения и события
 */
export async function fetchFeed(
  roomId: string,
  limit?: number
): Promise<FeedResponse['items']> {
  const q = limit != null ? `?limit=${limit}` : ''
  const res = await apiFetch<FeedResponse>(`/api/rooms/${roomId}/feed${q}`)
  return res.items ?? []
}
