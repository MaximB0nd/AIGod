/**
 * Шапка чата с названием и действиями
 */

import type { Chat } from '@/types/chat'
import styles from './ChatView.module.css'

interface ChatHeaderProps {
  chat: Chat
  onClose?: () => void
  onAddCharacter?: () => void
  onDelete?: () => void
}

export function ChatHeader({ chat, onClose, onAddCharacter, onDelete }: ChatHeaderProps) {
  return (
    <header className={styles.header}>
      {onClose && (
        <button
          type="button"
          className={styles.headerCloseBtn}
          onClick={onClose}
          title="Закрыть чат"
          aria-label="Закрыть чат"
        >
          ×
        </button>
      )}
      <div className={styles.headerAvatar}>
        {chat.avatar ? (
          <img src={chat.avatar} alt="" />
        ) : (
          <span>{chat.title.slice(0, 2).toUpperCase()}</span>
        )}
      </div>
      <div className={styles.headerInfo}>
        <h2 className={styles.headerTitle}>{chat.title}</h2>
        <span className={styles.headerSubtitle}>
          {chat.characterIds.length} персонаж(ей)
        </span>
      </div>
      <div className={styles.headerActions}>
        {onAddCharacter && (
          <button
            type="button"
            className={styles.headerBtn}
            onClick={onAddCharacter}
            title="Добавить персонажа"
          >
            +
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            className={styles.headerBtn}
            onClick={onDelete}
            title="Удалить чат"
          >
            🗑
          </button>
        )}
      </div>
    </header>
  )
}
