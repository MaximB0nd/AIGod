/**
 * Хук для загрузки воспоминаний агента
 * Готов для будущего UI (например, панель агента)
 */

import { useState, useCallback, useEffect } from 'react'
import * as agentsApi from '@/api/agents'
import type { Memory } from '@/types/agent'

export function useAgentMemories(roomId: string | null, agentId: string | null) {
  const [memories, setMemories] = useState<Memory[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (limit = 20, offset = 0) => {
    if (!roomId || !agentId) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await agentsApi.fetchAgentMemories(roomId, agentId, { limit, offset })
      setMemories(res.memories)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      setMemories([])
      setTotal(0)
    } finally {
      setIsLoading(false)
    }
  }, [roomId, agentId])

  useEffect(() => {
    if (roomId && agentId) load()
  }, [roomId, agentId, load])

  return { memories, total, isLoading, error, reload: load }
}
