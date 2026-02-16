/**
 * Модалка создания чата
 */

import { useState, useCallback } from 'react'
import { useChat } from '@/context/ChatContext'
import styles from './CreateChatModal.module.css'

interface CreateChatModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CreateChatModal({ isOpen, onClose }: CreateChatModalProps) {
  const { characters, createChat } = useChat()
  const [title, setTitle] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const toggleCharacter = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const trimmed = title.trim()
      if (!trimmed || selectedIds.size === 0) return
      await createChat({ title: trimmed, characterIds: [...selectedIds] })
      setTitle('')
      setSelectedIds(new Set())
      onClose()
    },
    [title, selectedIds, createChat, onClose]
  )

  const handleClose = useCallback(() => {
    setTitle('')
    setSelectedIds(new Set())
    onClose()
  }, [onClose])

  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Новый чат</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.label}>
            Название чата
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например: Философия vs Юмор"
              className={styles.input}
              autoFocus
            />
          </label>
          <label className={styles.label}>
            Персонажи (выберите минимум одного)
            <div className={styles.charList}>
              {characters.map((c) => (
                <label key={c.id} className={styles.charItem}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(c.id)}
                    onChange={() => toggleCharacter(c.id)}
                  />
                  <span>{c.name}</span>
                </label>
              ))}
            </div>
          </label>
          <div className={styles.actions}>
            <button type="button" className={styles.cancelBtn} onClick={handleClose}>
              Отмена
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={!title.trim() || selectedIds.size === 0}
            >
              Создать
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
