/**
 * WebSocket чата комнаты
 * WS /api/rooms/{roomId}/chat — сообщения и события в реальном времени
 * @see WEBSOCKET_CLIENT.md v1.0.0
 */

import { useEffect, useRef } from 'react'
import { getApiBase, getToken } from '@/api/client'

export type StreamMessage =
  | { type: 'connected'; payload?: { roomId?: string; message?: string } }
  | { type: 'message'; payload?: Record<string, unknown> }
  | { type: 'event'; payload?: Record<string, unknown> }
  | { type: 'pong'; payload?: Record<string, unknown> }
  | { type: 'error'; payload?: { message?: string } }

const PING_INTERVAL_MS = 25000
const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 5

function getWsBase(): string {
  const base = getApiBase()
  return base.replace(/^http/, 'ws')
}

export function useRoomStream({
  roomId,
  onMessage,
  enabled = true,
  onReconnect,
}: {
  roomId: string | null
  onMessage: (msg: StreamMessage) => void
  enabled?: boolean
  /** Вызывается при переподключении — можно обновить ленту (roomId передаётся для корректности) */
  onReconnect?: (roomId: string) => void
}) {
  const wsRef = useRef<WebSocket | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onMessageRef = useRef(onMessage)
  const onReconnectRef = useRef(onReconnect)
  onMessageRef.current = onMessage
  onReconnectRef.current = onReconnect

  useEffect(() => {
    if (!enabled || !roomId) return

    const token = getToken()
    if (!token) return

    const connect = () => {
      const wsUrl = `${getWsBase()}/api/rooms/${roomId}/chat?token=${encodeURIComponent(token)}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        reconnectAttemptRef.current = 0
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, PING_INTERVAL_MS)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as StreamMessage
          onMessageRef.current(msg)
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = (event) => {
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }
        wsRef.current = null

        if (event.code === 4001) console.error('WebSocket: не авторизован')
        if (event.code === 4003) console.error('WebSocket: нет доступа к комнате')

        // Reconnect при неожиданном закрытии (не 4001/4003)
        if (event.code !== 4001 && event.code !== 4003 && reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptRef.current += 1
          const currentRoomId = roomId
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null
            onReconnectRef.current?.(currentRoomId)
            connect()
          }, RECONNECT_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [roomId, enabled])

  return { ws: wsRef.current }
}
