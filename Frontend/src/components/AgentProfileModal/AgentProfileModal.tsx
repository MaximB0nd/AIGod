/**
 * Модалка профиля агента
 * Полная информация + воспоминания (GET /api/rooms/{roomId}/agents/{agentId}, memories)
 */

import { useState, useEffect, useCallback } from 'react'
import { fetchAgent, fetchAgentMemories } from '@/api/agents'
import type { Agent, Memory } from '@/types/agent'
import styles from './AgentProfileModal.module.css'

interface AgentProfileModalProps {
  isOpen: boolean
  onClose: () => void
  roomId: string
  agentId: string | null
}

function formatMemoryTime(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AgentProfileModal({ isOpen, onClose, roomId, agentId }: AgentProfileModalProps) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [memoriesTotal, setMemoriesTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    if (!roomId || !agentId) return
    setLoading(true)
    setError(null)
    try {
      const [agentData, memoriesData] = await Promise.all([
        fetchAgent(roomId, agentId),
        fetchAgentMemories(roomId, agentId, { limit: 50, offset: 0 }),
      ])
      setAgent(agentData)
      setMemories(memoriesData.memories ?? [])
      setMemoriesTotal(memoriesData.total ?? 0)
    } catch {
      setError('Ошибка загрузки профиля')
      setAgent(null)
      setMemories([])
    } finally {
      setLoading(false)
    }
  }, [roomId, agentId])

  useEffect(() => {
    if (isOpen && roomId && agentId) {
      loadProfile()
    } else {
      setAgent(null)
      setMemories([])
      setError(null)
    }
  }, [isOpen, roomId, agentId, loadProfile])

  const handleOverlayClick = useCallback(() => {
    onClose()
  }, [onClose])

  const handleModalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
  }, [])

  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={handleOverlayClick}>
      <div className={styles.modal} onClick={handleModalClick}>
        <div className={styles.header}>
          <h2>Профиль агента</h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>
        <div className={styles.body}>
          {loading && (
            <p className={styles.loading}>Загрузка...</p>
          )}
          {error && (
            <p className={styles.error}>{error}</p>
          )}
          {!loading && !error && agent && (
            <>
              <div className={styles.avatarRow}>
                <div
                  className={styles.avatar}
                  style={agent.mood?.color ? { backgroundColor: agent.mood.color } : undefined}
                >
                  {agent.avatar ? (
                    <img src={agent.avatar} alt="" />
                  ) : (
                    <span>{agent.name.slice(0, 2).toUpperCase()}</span>
                  )}
                </div>
                <div className={styles.titleBlock}>
                  <h3 className={styles.title}>{agent.name}</h3>
                  <span className={styles.meta}>
                    {agent.mood?.icon && <span className={styles.moodIcon}>{agent.mood.icon}</span>}
                    {agent.mood?.mood ?? '—'} · уровень {agent.mood?.level != null ? Math.round(agent.mood.level * 100) : '—'}%
                  </span>
                </div>
              </div>

              {agent.character && (
                <div className={styles.section}>
                  <label className={styles.label}>Характер</label>
                  <p className={styles.characterText}>{agent.character}</p>
                </div>
              )}

              {agent.keyMemories && agent.keyMemories.length > 0 && (
                <div className={styles.section}>
                  <label className={styles.label}>Ключевые воспоминания (из профиля)</label>
                  <ul className={styles.memoriesList}>
                    {agent.keyMemories.map((m) => (
                      <li key={m.id} className={styles.memoryItem}>
                        <p className={styles.memoryContent}>{m.content}</p>
                        <span className={styles.memoryTime}>{formatMemoryTime(m.timestamp)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className={styles.section}>
                <label className={styles.label}>
                  Воспоминания
                  {memoriesTotal > 0 && (
                    <span className={styles.count}> ({memories.length} из {memoriesTotal})</span>
                  )}
                </label>
                {memories.length === 0 ? (
                  <p className={styles.noMemories}>Нет воспоминаний</p>
                ) : (
                  <ul className={styles.memoriesList}>
                    {memories.map((m) => (
                      <li key={m.id} className={styles.memoryItem}>
                        <p className={styles.memoryContent}>{m.content}</p>
                        <span className={styles.memoryTime}>{formatMemoryTime(m.timestamp)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
