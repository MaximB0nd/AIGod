/**
 * Модалка добавления персонажа в чат
 */

import { useCallback } from 'react'
import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import styles from './AddCharacterModal.module.css'

interface AddCharacterModalProps {
  isOpen: boolean
  chat: Chat | null
  onClose: () => void
}

export function AddCharacterModal({ isOpen, chat, onClose }: AddCharacterModalProps) {
  const { characters, addCharacterToChat } = useChat()

  const availableCharacters = characters.filter(
    (c) => chat && !chat.characterIds.includes(c.id)
  )

  const handleAdd = useCallback(
    async (characterId: string) => {
      if (!chat) return
      await addCharacterToChat(chat.id, characterId)
      onClose()
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
          {availableCharacters.length === 0 ? (
            <p className={styles.empty}>Все персонажи уже в чате</p>
          ) : (
            <ul className={styles.list}>
              {availableCharacters.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    className={styles.item}
                    onClick={() => handleAdd(c.id)}
                  >
                    <span className={styles.itemName}>{c.name}</span>
                    {c.description && (
                      <span className={styles.itemDesc}>{c.description}</span>
                    )}
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
