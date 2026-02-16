/**
 * Пузырёк сообщения в стиле Telegram
 */

import type { Message, Character } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import styles from './ChatView.module.css'

interface MessageBubbleProps {
  message: Message
  character: Character | undefined
  isOutgoing?: boolean
}

export function MessageBubble({ message, character, isOutgoing = false }: MessageBubbleProps) {
  const name = character?.name ?? 'Неизвестный'
  const time = formatChatTime(message.timestamp)

  return (
    <div className={`${styles.bubbleWrap} ${isOutgoing ? styles.outgoing : styles.incoming}`}>
      <div className={styles.bubble}>
        <div className={styles.bubbleHeader}>
          <span className={styles.author}>{name}</span>
          <span className={styles.time}>{time}</span>
        </div>
        <p className={styles.content}>{message.content}</p>
        {message.attachments?.length ? (
          <div className={styles.attachments}>
            {message.attachments.map((a) => (
              <div key={a.id} className={styles.attachment}>
                <span className={styles.attachmentIcon}>{a.type === 'file' ? '📄' : '🖼'}</span>
                <span>{a.name}</span>
                {a.size && <span className={styles.attachmentSize}>{formatSize(a.size)}</span>}
              </div>
            ))}
          </div>
        ) : null}
        {message.reactions?.length ? (
          <div className={styles.reactions}>
            {message.reactions.map((r, i) => (
              <span key={i} className={styles.reaction}>
                {r.emoji}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
