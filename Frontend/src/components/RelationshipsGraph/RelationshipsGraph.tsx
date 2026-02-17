/**
 * Граф взаимоотношений агентов в комнате
 * Использует GET /api/rooms/{roomId}/relationships
 */

import { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { ForceGraphMethods } from 'react-force-graph-2d'
import { useRelationships } from '@/hooks/useRelationships'
import type { RelationshipsResponse } from '@/api/agents'
import styles from './RelationshipsGraph.module.css'

interface RelationshipsGraphProps {
  roomId: string | null
  /** Вызывать reload при открытии панели */
  onPanelOpen?: boolean
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

export function RelationshipsGraph({ roomId, onPanelOpen }: RelationshipsGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined)
  const [dimensions, setDimensions] = useState({ width: 320, height: GRAPH_HEIGHT })
  const { data, isLoading, error, reload } = useRelationships(roomId)

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
        <p className={styles.error}>{error}</p>
      </div>
    )
  }

  if (!data || (data.nodes.length === 0 && data.edges.length === 0)) {
    return (
      <div className={styles.wrapper} ref={containerRef}>
        <p className={styles.placeholder}>Нет агентов и связей в комнате</p>
      </div>
    )
  }

  return (
    <div className={styles.wrapper} ref={containerRef}>
      <h3 className={styles.title}>Граф отношений</h3>
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
    </div>
  )
}
