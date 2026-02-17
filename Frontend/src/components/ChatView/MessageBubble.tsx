/**
 * Пузырь сообщения в чате
 */

import type { Message, Character } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import styles from './ChatView.module.css'

interface MessageBubbleProps {
  message: Message & { sender?: 'user' | 'agent' | 'system' }
  character?: Character
  isOutgoing: boolean
}

export function MessageBubble({ message, character, isOutgoing }: MessageBubbleProps) {
  const time = formatChatTime(message.timestamp)
  const authorName = isOutgoing ? 'Вы' : (character?.name ?? 'Агент')

  return (
    <div className={`${styles.bubbleWrap} ${isOutgoing ? styles.outgoing : styles.incoming}`}>
      <div className={styles.bubble}>
        <div className={styles.bubbleHeader}>
          <span className={styles.author}>{authorName}</span>
          <span className={styles.time}>{time}</span>
        </div>
        <p className={styles.content}>{message.content}</p>
      </div>
    </div>
  )
}
