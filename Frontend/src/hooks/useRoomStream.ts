/**
 * WebSocket-подключение к потоку комнаты
 * ws://.../api/rooms/{roomId}/stream?token=jwt
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { useEffect, useRef, useCallback } from 'react'
import { getApiBase, getToken } from '@/api/client'

export type StreamMessage =
  | { type: 'event'; payload: { id: string; eventType: string; agentIds: string[]; description: string; timestamp: string; moodImpact?: Record<string, number> } }
  | { type: 'message'; payload: { id: string; text: string; sender: 'user' | 'agent'; agentId?: string; timestamp: string } }
  | { type: 'agent_update'; payload: { agentId: string; mood: { mood: string; level: number; icon?: string; color?: string } } }

export interface UseRoomStreamOptions {
  roomId: string | null
  onMessage?: (msg: StreamMessage) => void
  enabled?: boolean
}

export function useRoomStream({ roomId, onMessage, enabled = true }: UseRoomStreamOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (!roomId || !enabled) return

    const token = getToken()
    const base = getApiBase()
    const wsBase = base ? base.replace(/^http/, 'ws') : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    const url = `${wsBase}/api/rooms/${roomId}/stream${token ? `?token=${token}` : ''}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as StreamMessage
        onMessageRef.current?.(data)
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      // reconnect handled by useEffect
    }

    ws.onclose = () => {
      wsRef.current = null
    }
  }, [roomId, enabled])

  useEffect(() => {
    if (!roomId || !enabled) {
      wsRef.current?.close()
      wsRef.current = null
      return
    }

    connect()

    return () => {
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [roomId, enabled, connect])

  return { connect }
}
