/**
 * Модалка создания комнаты
 * Контракт: POST /api/rooms { name, description? }
 */

import { useState, useCallback } from 'react'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import styles from './CreateChatModal.module.css'

interface CreateChatModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CreateChatModal({ isOpen, onClose }: CreateChatModalProps) {
  const { createChat } = useChat()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const trimmedName = name.trim()
      if (!trimmedName || isCreating) return
      setIsCreating(true)
      setError(null)
      try {
        await createChat({
          title: trimmedName,
          description: description.trim() || undefined,
        })
        setName('')
        setDescription('')
        onClose()
      } catch (err) {
        setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Ошибка создания комнаты')
      } finally {
        setIsCreating(false)
      }
    },
    [name, description, createChat, onClose, isCreating]
  )

  const handleClose = useCallback(() => {
    setName('')
    setDescription('')
    setError(null)
    onClose()
  }, [onClose])

  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Новая комната</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          {error && <p className={styles.error}>{error}</p>}
          <label className={styles.label}>
            Название комнаты
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Философия vs Юмор"
              className={styles.input}
              autoFocus
            />
          </label>
          <label className={styles.label}>
            Описание (необязательно)
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Кратко опишите комнату"
              className={styles.textarea}
              rows={3}
            />
          </label>
          <div className={styles.actions}>
            <button type="button" className={styles.cancelBtn} onClick={handleClose}>
              Отмена
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={!name.trim() || isCreating}
            >
              {isCreating ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
