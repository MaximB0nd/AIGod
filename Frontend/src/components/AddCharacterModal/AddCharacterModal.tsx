/**
 * Модалка добавления агента в комнату
 * POST /api/rooms/{roomId}/agents — name, character, avatar (опционально)
 * @see docs/BACKEND_API_REQUIREMENTS.md § 3.3
 */

import { useCallback, useState } from 'react'
import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import styles from './AddCharacterModal.module.css'

interface AddCharacterModalProps {
  isOpen: boolean
  chat: Chat | null
  onClose: () => void
}

export function AddCharacterModal({ isOpen, chat, onClose }: AddCharacterModalProps) {
  const { characterPresets, createAgentToChat } = useChat()
  const [name, setName] = useState('')
  const [character, setCharacter] = useState('')
  const [avatar, setAvatar] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleApplyPreset = useCallback(
    (presetId: string) => {
      const preset = characterPresets.find((p) => p.id === presetId)
      if (preset) {
        setName(preset.name)
        setCharacter(preset.character)
      }
    },
    [characterPresets]
  )

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const trimmedName = name.trim()
      const trimmedCharacter = character.trim()
      if (!chat || !trimmedName || !trimmedCharacter || isCreating) return

      setIsCreating(true)
      setError(null)
      try {
        await createAgentToChat(chat.id, {
          name: trimmedName,
          character: trimmedCharacter,
          ...(avatar.trim() && { avatar: avatar.trim() }),
        })
        setName('')
        setCharacter('')
        setAvatar('')
        onClose()
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Ошибка добавления агента'
        )
      } finally {
        setIsCreating(false)
      }
    },
    [chat, name, character, avatar, createAgentToChat, onClose, isCreating]
  )

  const handleClose = useCallback(() => {
    setName('')
    setCharacter('')
    setAvatar('')
    setError(null)
    onClose()
  }, [onClose])

  if (!isOpen || !chat) return null

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Добавить агента в «{chat.title}»</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          {error && <p className={styles.error}>{error}</p>}

          {characterPresets.length > 0 && (
            <div className={styles.presetsBlock}>
              <label className={styles.label}>Быстрый выбор</label>
              <div className={styles.presetChips}>
                {characterPresets.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    className={styles.presetChip}
                    onClick={() => handleApplyPreset(preset.id)}
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <label className={styles.label}>
            Имя агента
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Философ"
              className={styles.input}
              autoFocus
            />
          </label>

          <label className={styles.label}>
            Характер, описание личности
            <textarea
              value={character}
              onChange={(e) => setCharacter(e.target.value)}
              placeholder="Опишите личность и характер агента"
              className={styles.textarea}
              rows={4}
            />
          </label>

          <label className={styles.label}>
            URL аватара (необязательно)
            <input
              type="url"
              value={avatar}
              onChange={(e) => setAvatar(e.target.value)}
              placeholder="https://..."
              className={styles.input}
            />
          </label>

          <div className={styles.actions}>
            <button type="button" className={styles.cancelBtn} onClick={handleClose}>
              Отмена
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={!name.trim() || !character.trim() || isCreating}
            >
              {isCreating ? 'Добавление...' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
