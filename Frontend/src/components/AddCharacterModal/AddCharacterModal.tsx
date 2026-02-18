/**
 * Модалка добавления агента в комнату
 * POST /api/rooms/{roomId}/agents — name, character, avatar (опционально)
 * Шаблоны: GET /api/default-agents, GET /api/default-agents/{id}
 */

import { useCallback, useState } from 'react'
import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import { fetchDefaultAgent } from '@/api/chat'
import styles from './AddCharacterModal.module.css'

interface AddCharacterModalProps {
  isOpen: boolean
  chat: Chat | null
  onClose: () => void
}

export function AddCharacterModal({ isOpen, chat, onClose }: AddCharacterModalProps) {
  const { defaultAgents, createAgentToChat } = useChat()
  const [name, setName] = useState('')
  const [character, setCharacter] = useState('')
  const [avatar, setAvatar] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isLoadingPreset, setIsLoadingPreset] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleApplyPreset = useCallback(async (defaultAgentId: number) => {
    setIsLoadingPreset(true)
    setError(null)
    try {
      const template = await fetchDefaultAgent(defaultAgentId)
      setName(template.name)
      setCharacter(template.character)
      setAvatar(template.avatar ?? '')
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Не удалось загрузить шаблон'
      )
    } finally {
      setIsLoadingPreset(false)
    }
  }, [])

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

          {defaultAgents.length > 0 && (
            <div className={styles.presetsBlock}>
              <label className={styles.label}>Быстрый выбор</label>
              <div className={styles.presetChips}>
                {defaultAgents.map((agent) => (
                  <button
                    key={agent.id}
                    type="button"
                    className={styles.presetChip}
                    onClick={() => handleApplyPreset(agent.id)}
                    disabled={isLoadingPreset}
                  >
                    {agent.name}
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
