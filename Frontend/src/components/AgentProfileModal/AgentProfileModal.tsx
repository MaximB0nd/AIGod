/**
 * Модалка профиля агента
 * Полная информация: характер, воспоминания, планы, взаимоотношения с агентами комнаты
 * API: GET /api/rooms/{roomId}/agents/{agentId}, memories, plans, relationships
 */

import { useState, useEffect, useCallback } from 'react'
import {
  fetchAgent,
  fetchAgentMemories,
  fetchAgentPlans,
  fetchRelationships,
  updateRelationship,
} from '@/api/agents'
import { ApiError } from '@/api/client'
import type { Agent, Memory, Plan } from '@/types/agent'
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

function getRelationshipsForAgent(
  agentId: string,
  nodes: { id: string; name: string }[],
  edges: { from: string; to: string; agentName?: string; sympathyLevel: number }[]
): { otherAgentId: string; agentName: string; sympathyLevel: number }[] {
  const nodeMap = new Map(nodes.map((n) => [n.id, n.name]))
  return edges
    .filter((e) => e.from === agentId || e.to === agentId)
    .map((e) => {
      const otherId = e.from === agentId ? e.to : e.from
      const agentName = e.agentName ?? nodeMap.get(otherId) ?? `Агент ${otherId}`
      return { otherAgentId: otherId, agentName, sympathyLevel: e.sympathyLevel }
    })
}

function formatSympathy(level: number): string {
  if (level >= 0.7) return 'Очень положительное'
  if (level >= 0.3) return 'Положительное'
  if (level >= -0.3) return 'Нейтральное'
  if (level >= -0.7) return 'Отрицательное'
  return 'Очень отрицательное'
}

function getPlanStatusLabel(status: Plan['status']): string {
  const labels: Record<Plan['status'], string> = {
    pending: 'Ожидает',
    in_progress: 'В процессе',
    done: 'Выполнено',
  }
  return labels[status] ?? status
}

export function AgentProfileModal({ isOpen, onClose, roomId, agentId }: AgentProfileModalProps) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [memoriesTotal, setMemoriesTotal] = useState(0)
  const [plans, setPlans] = useState<Plan[]>([])
  const [relationships, setRelationships] = useState<{ otherAgentId: string; agentName: string; sympathyLevel: number }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  /** Агент удалён или не существует — показываем «Удалённый аккаунт» */
  const [isDeleted, setIsDeleted] = useState(false)
  /** Редактирование симпатии: otherAgentId или null */
  const [editingOtherId, setEditingOtherId] = useState<string | null>(null)
  const [editSympathy, setEditSympathy] = useState(0)
  const [updateLoading, setUpdateLoading] = useState(false)

  const loadProfile = useCallback(async () => {
    if (!roomId || !agentId) return
    setLoading(true)
    setError(null)
    setIsDeleted(false)
    try {
      const [agentData, memoriesData, plansData, relationshipsData] = await Promise.all([
        fetchAgent(roomId, agentId),
        fetchAgentMemories(roomId, agentId, { limit: 50, offset: 0 }),
        fetchAgentPlans(roomId, agentId),
        fetchRelationships(roomId),
      ])
      setAgent(agentData)
      setMemories(memoriesData.memories ?? [])
      setMemoriesTotal(memoriesData.total ?? 0)
      setPlans(plansData.plans ?? [])
      setRelationships(
        getRelationshipsForAgent(agentId, relationshipsData.nodes ?? [], relationshipsData.edges ?? [])
      )
    } catch (err) {
      setAgent(null)
      setMemories([])
      setPlans([])
      setRelationships([])
      const isNotFound = err instanceof ApiError && (err.status === 404 || err.status === 410)
      if (isNotFound) {
        setIsDeleted(true)
      } else {
        setError('Ошибка загрузки профиля')
      }
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
      setPlans([])
      setRelationships([])
      setError(null)
      setIsDeleted(false)
      setEditingOtherId(null)
    }
  }, [isOpen, roomId, agentId, loadProfile])

  const handleOverlayClick = useCallback(() => {
    onClose()
  }, [onClose])

  const handleModalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
  }, [])

  const handleStartEdit = useCallback((r: { otherAgentId: string; sympathyLevel: number }) => {
    setEditingOtherId(r.otherAgentId)
    setEditSympathy(r.sympathyLevel)
  }, [])

  const handleCancelEdit = useCallback(() => {
    setEditingOtherId(null)
  }, [])

  const handleSaveRelationship = useCallback(async () => {
    if (!roomId || !agentId || !editingOtherId || updateLoading) return
    const id1 = parseInt(agentId, 10)
    const id2 = parseInt(editingOtherId, 10)
    if (Number.isNaN(id1) || Number.isNaN(id2)) return
    setUpdateLoading(true)
    try {
      await updateRelationship(roomId, {
        agent1Id: id1,
        agent2Id: id2,
        sympathyLevel: editSympathy,
      })
      setRelationships((prev) =>
        prev.map((r) =>
          r.otherAgentId === editingOtherId ? { ...r, sympathyLevel: editSympathy } : r
        )
      )
      setEditingOtherId(null)
    } catch {
      setError('Не удалось обновить отношение')
    } finally {
      setUpdateLoading(false)
    }
  }, [roomId, agentId, editingOtherId, editSympathy, updateLoading])

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
          {isDeleted && (
            <div className={styles.deletedAccount}>
              <div className={styles.deletedAvatar}>
                <span>?</span>
              </div>
              <h3 className={styles.deletedTitle}>Удалённый аккаунт</h3>
              <p className={styles.deletedText}>Этот агент был удалён или больше не существует.</p>
            </div>
          )}
          {!loading && !error && !isDeleted && agent && (
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
                  <p className={styles.emptyText}>Нет воспоминаний</p>
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

              <div className={styles.section}>
                <label className={styles.label}>Планы</label>
                {plans.length === 0 ? (
                  <p className={styles.emptyText}>Нет планов</p>
                ) : (
                  <ul className={styles.plansList}>
                    {plans.map((p) => (
                      <li key={p.id} className={styles.planItem} data-status={p.status}>
                        <p className={styles.planDescription}>{p.description}</p>
                        <span className={styles.planStatus}>{getPlanStatusLabel(p.status)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.section}>
                <label className={styles.label}>Взаимоотношения с агентами комнаты</label>
                {relationships.length === 0 ? (
                  <p className={styles.emptyText}>Нет данных об отношениях</p>
                ) : (
                  <ul className={styles.relationshipsList}>
                    {relationships.map((r, i) => (
                      <li key={`${r.agentName}-${i}`} className={styles.relationshipItem}>
                        {editingOtherId === r.otherAgentId ? (
                          <div className={styles.relationshipEdit}>
                            <span className={styles.relationshipName}>{r.agentName}</span>
                            <input
                              type="range"
                              min={-1}
                              max={1}
                              step={0.1}
                              value={editSympathy}
                              onChange={(e) => setEditSympathy(Number(e.target.value))}
                              className={styles.sympathySlider}
                              aria-label={`Симпатия к ${r.agentName}`}
                            />
                            <span className={styles.relationshipLevel}>
                              {Math.round(editSympathy * 100)}%
                            </span>
                            <div className={styles.relationshipEditActions}>
                              <button
                                type="button"
                                className={styles.editSaveBtn}
                                onClick={handleSaveRelationship}
                                disabled={updateLoading}
                              >
                                {updateLoading ? '…' : 'Сохранить'}
                              </button>
                              <button
                                type="button"
                                className={styles.editCancelBtn}
                                onClick={handleCancelEdit}
                                disabled={updateLoading}
                              >
                                Отмена
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <span className={styles.relationshipName}>{r.agentName}</span>
                            <div className={styles.relationshipRight}>
                              <span
                                className={styles.relationshipLevel}
                                title={`Уровень симпатии: ${(r.sympathyLevel * 100).toFixed(0)}%`}
                              >
                                {formatSympathy(r.sympathyLevel)} ({Math.round(r.sympathyLevel * 100)}%)
                              </span>
                              <button
                                type="button"
                                className={styles.editBtn}
                                onClick={() => handleStartEdit(r)}
                                title="Изменить уровень симпатии"
                                aria-label={`Изменить отношение к ${r.agentName}`}
                              >
                                ✎
                              </button>
                            </div>
                          </>
                        )}
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
