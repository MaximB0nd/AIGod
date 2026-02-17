/**
 * Граф взаимоотношений агентов в комнате
 * Использует GET /api/rooms/{roomId}/relationships
 */

import { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { ForceGraphMethods } from 'react-force-graph-2d'
import { useRelationships } from '@/hooks/useRelationships'
import type { RelationshipsResponse } from '@/api/agents'
import { startEmulation, stopEmulation, updateRoomSpeed } from '@/api/simulation'
import { fetchRoom } from '@/api/rooms'
import styles from './RelationshipsGraph.module.css'

interface RelationshipsGraphProps {
  roomId: string | null
  /** Вызывать reload при открытии панели */
  onPanelOpen?: boolean
  /**
   * Опциональный callback при старте/остановке эмуляции.
   * По умолчанию: POST /api/rooms/{roomId}/emulation/start и .../stop.
   */
  onEmulationToggle?: (roomId: string, running: boolean) => Promise<void>
}

function sympathyToColor(level: number): string {
  if (level >= 0) {
    const g = Math.round(34 + level * 220)
    const r = Math.round(255 - level * 180)
    return `rgb(${r}, ${g}, 94)`
  }
  const r = Math.round(255 + level * 180)
  const g = Math.round(34 - level * 34)
  return `rgb(${r}, ${g}, 94)`
}

function createForceBound(width: number, height: number, padding: number) {
  const xMin = -width / 2 + padding
  const xMax = width / 2 - padding
  const yMin = -height / 2 + padding
  const yMax = height / 2 - padding
  let nodes: Array<{ x?: number; y?: number; vx?: number; vy?: number }> = []
  function force() {
    nodes.forEach((n) => {
      const x = n.x ?? 0
      const y = n.y ?? 0
      const clampedX = Math.max(xMin, Math.min(xMax, x))
      const clampedY = Math.max(yMin, Math.min(yMax, y))
      ;(n as { x: number }).x = clampedX
      ;(n as { y: number }).y = clampedY
      if (clampedX !== x || clampedY !== y) {
        ;(n as { vx: number }).vx = 0
        ;(n as { vy: number }).vy = 0
      }
    })
  }
  ;(force as { initialize?: (n: Array<{ x?: number; y?: number }>) => void }).initialize = (
    n: Array<{ x?: number; y?: number }>
  ) => {
    nodes = n
  }
  return force
}

function transformToGraphData(data: RelationshipsResponse | null) {
  if (!data) return { nodes: [], links: [] }
  const nodes = data.nodes.map((n) => ({
    id: n.id,
    name: n.name,
    avatar: n.avatar,
    moodColor: n.mood?.color ?? '#94a3b8',
  }))
  const links = data.edges.map((e) => ({
    source: e.from,
    target: e.to,
    sympathyLevel: e.sympathyLevel,
  }))
  return { nodes, links }
}

const BOUND_PADDING = 60
const GRAPH_HEIGHT = 280
const SPEED_VALUES = [1, 2, 3] as const

export function RelationshipsGraph({ roomId, onPanelOpen, onEmulationToggle }: RelationshipsGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined)
  const [dimensions, setDimensions] = useState({ width: 320, height: GRAPH_HEIGHT })
  const [emulationRunning, setEmulationRunning] = useState(true)
  const [emulationLoading, setEmulationLoading] = useState(false)
  const [speed, setSpeed] = useState<1 | 2 | 3>(1)
  const [speedLoading, setSpeedLoading] = useState(false)
  const { data, isLoading, error, reload } = useRelationships(roomId)

  useEffect(() => {
    if (!roomId) return
    fetchRoom(roomId).then((room) => {
      if (room?.emulationRunning != null) {
        setEmulationRunning(room.emulationRunning)
      } else if (room?.speed != null) {
        setEmulationRunning(room.speed > 0)
      }
      if (room?.speed != null && SPEED_VALUES.includes(room.speed as 1 | 2 | 3)) {
        setSpeed(room.speed as 1 | 2 | 3)
      }
    }).catch(() => {})
  }, [roomId])

  const prevOpenRef = useRef(false)
  useEffect(() => {
    if (onPanelOpen && !prevOpenRef.current && roomId) {
      reload()
    }
    prevOpenRef.current = !!onPanelOpen
  }, [onPanelOpen, roomId, reload])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const { width } = entries[0]?.contentRect ?? { width: 320 }
      setDimensions({ width: Math.max(200, width), height: GRAPH_HEIGHT })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const graphData = useMemo(() => transformToGraphData(data), [data])

  const onGraphReady = useCallback((): void => {
    const g = graphRef.current
    if (!g) return
    g.d3Force('bound', createForceBound(dimensions.width, dimensions.height, BOUND_PADDING))
  }, [dimensions.width, dimensions.height])

  useEffect(() => {
    if (graphData.nodes.length > 0 && graphRef.current) {
      onGraphReady()
    }
  }, [graphData.nodes.length, dimensions, onGraphReady])

  const boundRef = useRef({ xMin: 0, xMax: 0, yMin: 0, yMax: 0 })
  boundRef.current = {
    xMin: -dimensions.width / 2 + BOUND_PADDING,
    xMax: dimensions.width / 2 - BOUND_PADDING,
    yMin: -dimensions.height / 2 + BOUND_PADDING,
    yMax: dimensions.height / 2 - BOUND_PADDING,
  }

  const onNodeDrag = useCallback((node: { x?: number; y?: number }) => {
    const { xMin, xMax, yMin, yMax } = boundRef.current
    const x = node.x ?? 0
    const y = node.y ?? 0
    ;(node as { x: number }).x = Math.max(xMin, Math.min(xMax, x))
    ;(node as { y: number }).y = Math.max(yMin, Math.min(yMax, y))
  }, [])

  const handleEmulationToggle = useCallback(async () => {
    if (!roomId || emulationLoading) return
    const nextRunning = !emulationRunning
    setEmulationLoading(true)
    try {
      if (onEmulationToggle) {
        await onEmulationToggle(roomId, nextRunning)
      } else if (nextRunning) {
        await startEmulation(roomId)
      } else {
        await stopEmulation(roomId)
      }
      setEmulationRunning(nextRunning)
    } catch {
      // Ошибка — состояние не меняем
    } finally {
      setEmulationLoading(false)
    }
  }, [roomId, emulationRunning, emulationLoading, onEmulationToggle])

  const handleSpeedChange = useCallback(
    async (newSpeed: 1 | 2 | 3) => {
      if (!roomId || speedLoading) return
      setSpeedLoading(true)
      try {
        await updateRoomSpeed(roomId, newSpeed)
        setSpeed(newSpeed)
      } catch {
        // Ошибка — состояние не меняем
      } finally {
        setSpeedLoading(false)
      }
    },
    [roomId, speedLoading]
  )

  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value) as 1 | 2 | 3
    setSpeed(v)
  }, [])

  const handleSliderRelease = useCallback(
    (e: React.PointerEvent<HTMLInputElement>) => {
      e.currentTarget.releasePointerCapture(e.pointerId)
      const v = Number(e.currentTarget.value) as 1 | 2 | 3
      handleSpeedChange(v)
    },
    [handleSpeedChange]
  )

  if (!roomId) {
    return (
      <div className={styles.wrapper}>
        <p className={styles.placeholder}>Выберите комнату</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className={styles.wrapper} ref={containerRef}>
        <p className={styles.loading}>Загрузка графа отношений...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={styles.wrapper} ref={containerRef}>
        <div className={styles.header}>
          <h3 className={styles.title}>Граф отношений</h3>
          <button
            type="button"
            className={styles.refreshBtn}
            onClick={() => reload()}
            disabled={isLoading}
            title="Обновить граф"
            aria-label="Обновить граф"
          >
            ↻
          </button>
        </div>
        <p className={styles.error}>{error}</p>
      </div>
    )
  }

  if (!data || (data.nodes.length === 0 && data.edges.length === 0)) {
    return (
      <div className={styles.wrapper} ref={containerRef}>
        <div className={styles.header}>
          <h3 className={styles.title}>Граф отношений</h3>
          <button
            type="button"
            className={styles.refreshBtn}
            onClick={() => reload()}
            disabled={isLoading}
            title="Обновить граф"
            aria-label="Обновить граф"
          >
            ↻
          </button>
        </div>
        <p className={styles.placeholder}>Нет агентов и связей в комнате</p>
      </div>
    )
  }

  return (
    <div className={styles.wrapper} ref={containerRef}>
      <div className={styles.header}>
        <h3 className={styles.title}>Граф отношений</h3>
        <button
          type="button"
          className={styles.refreshBtn}
          onClick={() => reload()}
          disabled={isLoading}
          title="Обновить граф"
          aria-label="Обновить граф"
        >
          ↻
        </button>
      </div>
      <div className={styles.graphContainer} style={{ height: dimensions.height }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="transparent"
          nodeId="id"
          linkSource="source"
          linkTarget="target"
          nodeLabel={(n) => (n as { name?: string }).name ?? ''}
          nodeColor={(n) => (n as { moodColor?: string }).moodColor ?? '#94a3b8'}
          nodeVal={4}
          linkColor={(l) => sympathyToColor((l as { sympathyLevel?: number }).sympathyLevel ?? 0)}
          linkWidth={1.5}
          linkLabel={(l) => {
            const level = (l as { sympathyLevel?: number }).sympathyLevel ?? 0
            const pct = Math.round(level * 100)
            return `Симпатия: ${pct}%`
          }}
          minZoom={1}
          maxZoom={1}
          enableZoomInteraction={false}
          enablePanInteraction={false}
          enableNodeDrag={true}
          onNodeDrag={onNodeDrag}
          d3VelocityDecay={0.4}
          onEngineStop={onGraphReady}
        />
      </div>
      <p className={styles.hint}>Цвет связи: красный — негатив, зелёный — позитив</p>
      <button
        type="button"
        className={styles.emulationBtn}
        onClick={handleEmulationToggle}
        disabled={emulationLoading}
        title={emulationRunning ? 'Остановить эмуляцию' : 'Запустить эмуляцию'}
        aria-label={emulationRunning ? 'Остановить эмуляцию' : 'Запустить эмуляцию'}
      >
        {emulationLoading ? '…' : emulationRunning ? '⏹ Остановить' : '▶ Старт'}
      </button>
      <div className={styles.speedBlock}>
        <label className={styles.speedLabel} htmlFor="speed-slider">
          Скорость
        </label>
        <input
          id="speed-slider"
          type="range"
          min={1}
          max={3}
          step={1}
          value={speed}
          onChange={handleSliderChange}
          onPointerDown={(e) => e.currentTarget.setPointerCapture(e.pointerId)}
          onPointerUp={handleSliderRelease}
          className={styles.speedSlider}
          aria-label="Скорость эмуляции"
        />
        <div className={styles.speedTicks}>
          {SPEED_VALUES.map((v) => (
            <button
              key={v}
              type="button"
              className={speed === v ? styles.speedTickActive : styles.speedTick}
              onClick={() => handleSpeedChange(v)}
              disabled={speedLoading}
              aria-pressed={speed === v}
            >
              {v}x
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
