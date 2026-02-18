/**
 * Хук для загрузки графа отношений агентов
 * Готов для будущего UI (визуализация связей)
 */

import { useState, useCallback, useEffect } from 'react'
import * as agentsApi from '@/api/agents'
import type { RelationshipsResponse } from '@/api/agents'

export function useRelationships(roomId: string | null) {
  const [data, setData] = useState<RelationshipsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!roomId) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await agentsApi.fetchRelationships(roomId)
      setData(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      setData(null)
    } finally {
      setIsLoading(false)
    }
  }, [roomId])

  useEffect(() => {
    if (roomId) load()
  }, [roomId, load])

  return { data, isLoading, error, reload: load }
}
