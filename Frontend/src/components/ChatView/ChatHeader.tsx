/**
 * Шапка чата с названием и действиями
 */

import type { Chat } from '@/types/chat'
import styles from './ChatView.module.css'

interface ChatHeaderProps {
  chat: Chat
  onClose?: () => void
  onAddCharacter?: () => void
  onToggleSidebar?: () => void
  sidebarCollapsed?: boolean
  /** Раскрыть/свернуть правую панель */
  onToggleRightPanel?: () => void
  rightPanelCollapsed?: boolean
  /** Клик по иконке/названию группы — открыть описание */
  onGroupClick?: () => void
}

export function ChatHeader({ chat, onClose, onAddCharacter, onToggleSidebar, sidebarCollapsed, onToggleRightPanel, rightPanelCollapsed, onGroupClick }: ChatHeaderProps) {
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
        {onToggleRightPanel && (
          <button
            type="button"
            className={styles.headerBtn}
            onClick={onToggleRightPanel}
            title={rightPanelCollapsed ? 'Развернуть правую панель' : 'Свернуть правую панель'}
            aria-label={rightPanelCollapsed ? 'Развернуть правую панель' : 'Свернуть правую панель'}
          >
            {rightPanelCollapsed ? '◀' : '▶'}
          </button>
        )}
      </div>
    </header>
  )
}
