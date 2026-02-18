/**
 * WebSocket графа отношений комнаты
 * WS /api/rooms/{roomId}/graph — обновления рёбер в реальном времени
 * @see WEBSOCKET_CLIENT.md v1.0.0
 */

import { useEffect, useRef } from 'react'
import { getApiBase, getToken } from '@/api/client'

export type GraphMessage =
  | { type: 'connected'; payload?: { roomId?: string; message?: string } }
  | { type: 'edge_update'; payload?: { roomId?: string; from?: string; to?: string; sympathyLevel?: number } }
  | { type: 'pong'; payload?: Record<string, unknown> }
  | { type: 'error'; payload?: { message?: string } }

const PING_INTERVAL_MS = 25000

function getWsBase(): string {
  const base = getApiBase()
  return base.replace(/^http/, 'ws')
}

export function useRoomGraph({
  roomId,
  onMessage,
  enabled = true,
}: {
  roomId: string | null
  onMessage: (msg: GraphMessage) => void
  enabled?: boolean
}) {
  const wsRef = useRef<WebSocket | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!enabled || !roomId) return

    const token = getToken()
    if (!token) return

    const wsUrl = `${getWsBase()}/api/rooms/${roomId}/graph?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL_MS)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as GraphMessage
        onMessageRef.current(msg)
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = (event) => {
      if (event.code === 4001) console.error('WebSocket graph: не авторизован')
      if (event.code === 4003) console.error('WebSocket graph: нет доступа к комнате')
    }

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
      ws.close()
      wsRef.current = null
    }
  }, [roomId, enabled])

  return { ws: wsRef.current }
}
