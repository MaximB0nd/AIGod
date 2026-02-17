/**
 * Модалка описания группы (комнаты)
 * Список агентов комнаты с возможностью удаления
 */

import { useState, useEffect, useCallback } from 'react'
import { fetchRoom } from '@/api/rooms'
import { fetchAgents } from '@/api/agents'
import { useChat } from '@/context/ChatContext'
import { AgentProfileModal } from '@/components/AgentProfileModal'
import type { Room } from '@/types/room'
import type { Chat } from '@/types/chat'
import type { AgentSummary } from '@/types/agent'
import styles from './GroupInfoModal.module.css'

interface GroupInfoModalProps {
  isOpen: boolean
  onClose: () => void
  /** Чат = комната (roomId = chat.id) */
  chat: Chat | null
}

export function GroupInfoModal({ isOpen, onClose, chat }: GroupInfoModalProps) {
  const { removeCharacterFromChat } = useChat()
  const [room, setRoom] = useState<Room | null>(null)
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [profileAgentId, setProfileAgentId] = useState<string | null>(null)

  const loadRoom = useCallback(async () => {
    if (!chat?.id) return
    setLoading(true)
    setError(null)
    try {
      const [roomData, agentsData] = await Promise.all([
        fetchRoom(chat.id),
        fetchAgents(chat.id),
      ])
      setRoom(roomData ?? null)
      setAgents(agentsData ?? [])
      if (!roomData) setError('Не удалось загрузить данные')
    } catch {
      setError('Ошибка загрузки')
      setRoom(null)
      setAgents([])
    } finally {
      setLoading(false)
    }
  }, [chat?.id])

  useEffect(() => {
    if (isOpen && chat?.id) {
      loadRoom()
    } else {
      setRoom(null)
      setAgents([])
      setError(null)
      setDeletingId(null)
      setProfileAgentId(null)
    }
  }, [isOpen, chat?.id, loadRoom])

  const handleRemoveAgent = useCallback(
    async (agentId: string) => {
      if (!chat?.id || deletingId) return
      setDeletingId(agentId)
      try {
        await removeCharacterFromChat(chat.id, agentId)
        setAgents((prev) => prev.filter((a) => a.id !== agentId))
        setRoom((prev) =>
          prev
            ? { ...prev, agentCount: Math.max(0, (prev.agentCount ?? 0) - 1) }
            : null
        )
      } catch {
        setError('Не удалось удалить агента')
      } finally {
        setDeletingId(null)
      }
    },
    [chat?.id, removeCharacterFromChat, deletingId]
  )

  const handleRemoveClick = useCallback(
    (e: React.MouseEvent, agent: AgentSummary) => {
      e.stopPropagation()
      e.preventDefault()
      if (!window.confirm(`Удалить агента «${agent.name}» из комнаты?`)) return
      handleRemoveAgent(agent.id)
    },
    [handleRemoveAgent]
  )

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
          <h2>Описание группы</h2>
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
          {!loading && !error && room && (
            <>
              <div className={styles.avatarRow}>
                <div className={styles.avatar}>
                  {chat?.avatar ? (
                    <img src={chat.avatar} alt="" />
                  ) : (
                    <span>{(room.name || chat?.title || 'Группа').slice(0, 2).toUpperCase()}</span>
                  )}
                </div>
                <div className={styles.titleBlock}>
                  <h3 className={styles.title}>{room.name || chat?.title || 'Группа'}</h3>
                  <span className={styles.meta}>
                    {room.agentCount ?? agents.length ?? chat?.characterIds.length ?? 0} агентов
                    {room.speed != null && ` · Скорость ${room.speed}x`}
                  </span>
                </div>
              </div>
              {room.description ? (
                <div className={styles.description}>
                  <label className={styles.label}>Описание</label>
                  <p className={styles.descriptionText}>{room.description}</p>
                </div>
              ) : (
                <p className={styles.noDescription}>
                  Описание не задано.
                </p>
              )}
              <div className={styles.agentsSection}>
                <label className={styles.label}>Агенты в комнате</label>
                {agents.length === 0 ? (
                  <p className={styles.noAgents}>Нет агентов</p>
                ) : (
                  <ul className={styles.agentsList}>
                    {agents.map((agent) => (
                      <li key={agent.id} className={styles.agentItem}>
                        <div
                          role="button"
                          tabIndex={0}
                          className={styles.agentCard}
                          onClick={() => setProfileAgentId(agent.id)}
                          onKeyDown={(e) => e.key === 'Enter' && setProfileAgentId(agent.id)}
                        >
                          <div className={styles.agentAvatar}>
                            {agent.avatar ? (
                              <img src={agent.avatar} alt="" />
                            ) : (
                              <span>{agent.name.slice(0, 2).toUpperCase()}</span>
                            )}
                          </div>
                          <span className={styles.agentName}>{agent.name}</span>
                          <button
                            type="button"
                            className={styles.removeBtn}
                            onClick={(e) => handleRemoveClick(e, agent)}
                            disabled={!!deletingId}
                            title="Удалить агента из комнаты"
                            aria-label={`Удалить ${agent.name}`}
                          >
                            {deletingId === agent.id ? '…' : '×'}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      <AgentProfileModal
        isOpen={!!profileAgentId}
        onClose={() => setProfileAgentId(null)}
        roomId={chat?.id ?? ''}
        agentId={profileAgentId}
      />
    </div>
  )
}
