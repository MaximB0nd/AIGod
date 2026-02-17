/**
 * Хук для загрузки планов агента
 * Готов для будущего UI (панель планов)
 */

import { useState, useCallback, useEffect } from 'react'
import * as agentsApi from '@/api/agents'
import type { Plan } from '@/types/agent'

export function useAgentPlans(roomId: string | null, agentId: string | null) {
  const [plans, setPlans] = useState<Plan[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!roomId || !agentId) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await agentsApi.fetchAgentPlans(roomId, agentId)
      setPlans(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки')
      setPlans([])
    } finally {
      setIsLoading(false)
    }
  }, [roomId, agentId])

  useEffect(() => {
    if (roomId && agentId) load()
  }, [roomId, agentId, load])

  return { plans, isLoading, error, reload: load }
}
