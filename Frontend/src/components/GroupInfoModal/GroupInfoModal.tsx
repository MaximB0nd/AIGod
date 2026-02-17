/**
 * Модалка описания группы (комнаты)
 * Bento-стиль, заготовка под подключение бэкенда
 */

import { useState, useEffect, useCallback } from 'react'
import { fetchRoom } from '@/api/rooms'
import type { Room } from '@/types/room'
import type { Chat } from '@/types/chat'
import styles from './GroupInfoModal.module.css'

interface GroupInfoModalProps {
  isOpen: boolean
  onClose: () => void
  /** Чат = комната (roomId = chat.id) */
  chat: Chat | null
}

export function GroupInfoModal({ isOpen, onClose, chat }: GroupInfoModalProps) {
  const [room, setRoom] = useState<Room | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadRoom = useCallback(async () => {
    if (!chat?.id) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchRoom(chat.id)
      setRoom(data ?? null)
      if (!data) setError('Не удалось загрузить данные')
    } catch {
      setError('Ошибка загрузки')
      setRoom(null)
    } finally {
      setLoading(false)
    }
  }, [chat?.id])

  useEffect(() => {
    if (isOpen && chat?.id) {
      loadRoom()
    } else {
      setRoom(null)
      setError(null)
    }
  }, [isOpen, chat?.id, loadRoom])

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
                    {room.agentCount ?? chat?.characterIds.length ?? 0} агентов
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
                  Описание не задано. После подключения бэкенда можно будет редактировать.
                </p>
              )}
              {/* TODO: кнопки редактирования, удаления — после подключения PATCH/DELETE */}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
