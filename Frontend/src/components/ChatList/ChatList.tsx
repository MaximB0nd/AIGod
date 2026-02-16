/**
 * Список чатов (левая панель в стиле Telegram)
 */

import { useChat } from '@/context/ChatContext'
import { ChatListItem } from './ChatListItem'
import styles from './ChatList.module.css'

interface ChatListProps {
  onCreateChat: () => void
}

export function ChatList({ onCreateChat }: ChatListProps) {
  const { chats, activeChat, selectChat } = useChat()

  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <h1 className={styles.title}>Чаты нейросетей</h1>
        <button
          type="button"
          className={styles.createBtn}
          onClick={onCreateChat}
          title="Создать чат"
          aria-label="Создать чат"
        >
          +
        </button>
      </div>
      <ul className={styles.list}>
        {chats.map((chat) => (
          <ChatListItem
            key={chat.id}
            chat={chat}
            isActive={activeChat?.id === chat.id}
            onClick={() => selectChat(chat)}
          />
        ))}
      </ul>
    </aside>
  )
}
