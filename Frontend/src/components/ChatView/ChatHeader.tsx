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
  onToggleSidebar?: () => void
  sidebarCollapsed?: boolean
  /** Клик по иконке/названию группы — открыть описание */
  onGroupClick?: () => void
}

export function ChatHeader({ chat, onClose, onAddCharacter, onDelete, onToggleSidebar, sidebarCollapsed, onGroupClick }: ChatHeaderProps) {
  return (
    <header className={styles.header}>
      {onToggleSidebar && (
        <button
          type="button"
          className={styles.headerToggleBtn}
          onClick={onToggleSidebar}
          title={sidebarCollapsed ? 'Развернуть панель' : 'Свернуть панель'}
          aria-label={sidebarCollapsed ? 'Развернуть панель' : 'Свернуть панель'}
        >
          {sidebarCollapsed ? '▶' : '◀'}
        </button>
      )}
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
      {onGroupClick ? (
        <button
          type="button"
          className={styles.headerGroup}
          onClick={onGroupClick}
          title="Описание группы"
          aria-label="Открыть описание группы"
        >
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
              {chat.characterIds.length} агентов
            </span>
          </div>
        </button>
      ) : (
        <>
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
              {chat.characterIds.length} агентов
            </span>
          </div>
        </>
      )}
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
