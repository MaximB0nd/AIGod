/**
 * Модалка добавления персонажа в чат
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
  const { characterPresets, addCharacterToChat } = useChat()
  const [addingId, setAddingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const availableCharacters = characterPresets

  const handleAdd = useCallback(
    async (presetId: string) => {
      if (!chat) return
      setAddingId(presetId)
      setError(null)
      try {
        await addCharacterToChat(chat.id, presetId)
        onClose()
      } catch (err) {
        setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Ошибка добавления персонажа')
      } finally {
        setAddingId(null)
      }
    },
    [chat, addCharacterToChat, onClose]
  )

  if (!isOpen || !chat) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>Добавить персонажа в «{chat.title}»</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <div className={styles.content}>
          {error && <p className={styles.error}>{error}</p>}
          {availableCharacters.length === 0 ? (
            <p className={styles.empty}>Все персонажи уже в чате</p>
          ) : (
            <ul className={styles.list}>
              {availableCharacters.map((preset) => (
                <li key={preset.id}>
                  <button
                    type="button"
                    className={styles.item}
                    onClick={() => handleAdd(preset.id)}
                    disabled={addingId === preset.id}
                  >
                    <span className={styles.itemName}>{preset.name}</span>
                    {preset.description && (
                      <span className={styles.itemDesc}>{preset.description}</span>
                    )}
                    {addingId === preset.id && <span className={styles.adding}>...</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
