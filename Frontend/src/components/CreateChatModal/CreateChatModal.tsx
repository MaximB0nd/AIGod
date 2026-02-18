/**
 * Модалка создания комнаты
 * Контракт: POST /api/rooms { name, description?, orchestration_type }
 * @see API_DOCS.md v1.0.0
 */

import { useState, useCallback } from 'react'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import styles from './CreateChatModal.module.css'

export type OrchestrationType = 'single' | 'circular' | 'narrator' | 'full_context'

const ORCHESTRATION_OPTIONS: { value: OrchestrationType; label: string; desc: string }[] = [
  { value: 'single', label: 'Single', desc: 'Один агент отвечает на сообщение' },
  { value: 'circular', label: 'Circular', desc: 'Агенты отвечают по кругу' },
  { value: 'narrator', label: 'Narrator', desc: 'Ведущий координирует диалог' },
  { value: 'full_context', label: 'Full Context', desc: 'Все агенты видят полный контекст' },
]

interface CreateChatModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CreateChatModal({ isOpen, onClose }: CreateChatModalProps) {
  const { createChat } = useChat()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [orchestrationType, setOrchestrationType] = useState<OrchestrationType>('single')
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
          orchestration_type: orchestrationType,
        })
        setName('')
        setDescription('')
        setOrchestrationType('single')
        onClose()
      } catch (err) {
        setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Ошибка создания комнаты')
      } finally {
        setIsCreating(false)
      }
    },
    [name, description, orchestrationType, createChat, onClose, isCreating]
  )

  const handleClose = useCallback(() => {
    setName('')
    setDescription('')
    setOrchestrationType('single')
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
              rows={2}
            />
          </label>
          <div className={styles.bentoSection}>
            <span className={styles.sectionLabel}>Режим оркестрации</span>
            <div className={styles.bentoGrid}>
              {ORCHESTRATION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`${styles.bentoCard} ${orchestrationType === opt.value ? styles.bentoCardActive : ''}`}
                  onClick={() => setOrchestrationType(opt.value)}
                >
                  <span className={styles.bentoCardLabel}>{opt.label}</span>
                  <span className={styles.bentoCardDesc}>{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>
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
