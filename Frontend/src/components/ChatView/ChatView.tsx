/**
 * Окно чата (правая панель в стиле Telegram)
 */

import { useRef, useEffect, useCallback } from 'react'
import { useChat } from '@/context/ChatContext'
import { MessageBubble } from './MessageBubble'
import { ChatHeader } from './ChatHeader'
import { MessageInput } from './MessageInput'
import styles from './ChatView.module.css'

interface ChatViewProps {
  onAddCharacter?: () => void
  onDeleteChat?: () => void
}

export function ChatView({ onAddCharacter, onDeleteChat }: ChatViewProps) {
  const { activeChat, messages, characters, selectChat } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)

  const handleCloseChat = useCallback(() => {
    selectChat(null)
  }, [selectChat])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  if (!activeChat) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyContent}>
          <p>Выберите чат или создайте новый</p>
          <span>Чаты нейросетей — персонажи общаются друг с другом</span>
        </div>
      </div>
    )
  }

  const getCharacter = (id: string) => characters.find((c) => c.id === id)

  return (
    <div className={styles.chat}>
      <ChatHeader
        chat={activeChat}
        onClose={handleCloseChat}
        onAddCharacter={onAddCharacter}
        onDelete={onDeleteChat}
      />
      <div className={styles.messages} ref={scrollRef}>
        <div className={styles.messagesInner}>
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              character={getCharacter(msg.characterId)}
              isOutgoing={false}
            />
          ))}
        </div>
      </div>
      <MessageInput chat={activeChat} />
    </div>
  )
}
