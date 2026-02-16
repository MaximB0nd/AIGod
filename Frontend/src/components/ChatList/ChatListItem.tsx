/**
 * Элемент списка чатов
 */

import type { Chat } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import styles from './ChatList.module.css'

interface ChatListItemProps {
  chat: Chat
  isActive: boolean
  onClick: () => void
}

export function ChatListItem({ chat, isActive, onClick }: ChatListItemProps) {
  const lastPreview = chat.lastMessage?.content ?? 'Нет сообщений'
  const truncated = lastPreview.length > 35 ? `${lastPreview.slice(0, 35)}...` : lastPreview
  const time = chat.lastMessage?.timestamp
    ? formatChatTime(chat.lastMessage.timestamp)
    : ''

  return (
    <li>
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
    </li>
  )
}
