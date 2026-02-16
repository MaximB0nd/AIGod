/**
 * Элемент списка чатов
 */

import { useState, useEffect } from 'react'
import type { Chat } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import styles from './ChatList.module.css'

interface ChatListItemProps {
  chat: Chat
  isActive: boolean
  onClick: () => void
  onDelete: (chat: Chat) => void
  onAddCharacter: (chat: Chat) => void
}

export function ChatListItem({ chat, isActive, onClick, onDelete, onAddCharacter }: ChatListItemProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })

  const lastPreview = chat.lastMessage?.content ?? 'Нет сообщений'
  const truncated = lastPreview.length > 35 ? `${lastPreview.slice(0, 35)}...` : lastPreview
  const time = chat.lastMessage?.timestamp
    ? formatChatTime(chat.lastMessage.timestamp)
    : ''

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setMenuPos({ x: e.clientX, y: e.clientY })
    setMenuOpen(true)
  }

  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(false)
    document.addEventListener('click', close)
    document.addEventListener('contextmenu', close)
    return () => {
      document.removeEventListener('click', close)
      document.removeEventListener('contextmenu', close)
    }
  }, [menuOpen])

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    onDelete(chat)
  }

  const handleAddCharacter = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    onAddCharacter(chat)
  }

  return (
    <li onContextMenu={handleContextMenu}>
      <button
        type="button"
        className={`${styles.item} ${isActive ? styles.active : ''}`}
        onClick={onClick}
      >
        <div className={styles.avatar}>
          {chat.avatar ? (
            <img src={chat.avatar} alt="" />
          ) : (
            <span className={styles.avatarPlaceholder}>
              {chat.title.slice(0, 2).toUpperCase()}
            </span>
          )}
          {chat.unreadCount != null && chat.unreadCount > 0 && (
            <span className={styles.badge}>{chat.unreadCount}</span>
          )}
        </div>
        <div className={styles.content}>
          <div className={styles.top}>
            <span className={styles.name}>{chat.title}</span>
            {time && <span className={styles.time}>{time}</span>}
          </div>
          <p className={styles.preview}>{truncated}</p>
        </div>
      </button>
      {menuOpen && (
        <div
          className={styles.contextMenu}
          style={{ left: menuPos.x, top: menuPos.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button type="button" className={styles.contextMenuItem} onClick={handleAddCharacter}>
            Добавить персонажа
          </button>
          <button type="button" className={`${styles.contextMenuItem} ${styles.contextMenuDanger}`} onClick={handleDelete}>
            Удалить
          </button>
        </div>
      )}
    </li>
  )
}
