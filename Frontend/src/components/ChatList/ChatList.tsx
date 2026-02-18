/**
 * Список чатов (левая панель в стиле Telegram)
 */

import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { useAuth } from '@/context/AuthContext'
import { ChatListItem } from './ChatListItem'
import styles from './ChatList.module.css'

interface ChatListProps {
  onCreateChat: () => void
  onDeleteChat: (chat: Chat) => void
  onAddCharacter: (chat: Chat) => void
}

export function ChatList({ onCreateChat, onDeleteChat, onAddCharacter }: ChatListProps) {
  const { chats, activeChat, selectChat } = useChat()
  const { user, logout } = useAuth()

  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <img src="/logo.png" alt="" className={styles.headerLogo} />
          <h1 className={styles.title}>Комнаты</h1>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.userName} title={user?.email}>{user?.username ?? '—'}</span>
          <button
            type="button"
            className={styles.createBtn}
            onClick={onCreateChat}
            title="Создать комнату"
            aria-label="Создать комнату"
          >
            +
          </button>
          <button
            type="button"
            className={styles.logoutBtn}
            onClick={logout}
            title="Выйти"
            aria-label="Выйти"
          >
            <span className={styles.logoutBtnText}>Выход</span>
          </button>
        </div>
      </div>
      <ul className={styles.list}>
        {chats.map((chat) => (
          <ChatListItem
            key={chat.id}
            chat={chat}
            isActive={activeChat?.id === chat.id}
            onClick={() => selectChat(chat)}
            onDelete={onDeleteChat}
            onAddCharacter={onAddCharacter}
          />
        ))}
      </ul>
    </aside>
  )
}
