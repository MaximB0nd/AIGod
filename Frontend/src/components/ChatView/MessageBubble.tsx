/**
 * Пузырь сообщения в чате
 */

import type { Message, Character } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import { useTts } from '@/context/TtsContext'
import styles from './ChatView.module.css'

interface MessageBubbleProps {
  message: Message & { sender?: 'user' | 'agent' | 'system' }
  character?: Character
  isOutgoing: boolean
  /** При клике на аватар — открыть профиль агента (только для входящих) */
  onAvatarClick?: (agentId: string) => void
}

export function MessageBubble({ message, character, isOutgoing, onAvatarClick }: MessageBubbleProps) {
  const time = formatChatTime(message.timestamp)
  const authorName = isOutgoing ? 'Вы' : (character?.name ?? 'Агент')
  const { playingMessageId, play, stop } = useTts()
  const hasContent = Boolean(message.content?.trim())
  const isPlaying = playingMessageId === message.id

  const handleTtsClick = () => {
    if (isPlaying) stop()
    else play(message.id, message.content)
  }

  const handleAvatarClick = () => {
    if (message.characterId && onAvatarClick) onAvatarClick(message.characterId)
  }

  const renderAgentAvatar = () => {
    const displayName = character?.name ?? 'Агент'
    const initials = displayName.slice(0, 2).toUpperCase() || '?'
    const avatarContent = character?.avatar ? (
      <img src={character.avatar} alt="" />
    ) : (
      <span>{initials}</span>
    )

    const avatarEl = (
      <div className={styles.messageAvatar} title={`Профиль: ${displayName}`}>
        {avatarContent}
      </div>
    )

    if (message.characterId && onAvatarClick) {
      return (
        <button
          type="button"
          className={styles.messageAvatarBtn}
          onClick={handleAvatarClick}
          aria-label={`Открыть профиль ${displayName}`}
        >
          {avatarEl}
        </button>
      )
    }
    return <div className={styles.messageAvatarWrap}>{avatarEl}</div>
  }

  return (
    <div className={`${styles.bubbleWrap} ${isOutgoing ? styles.outgoing : styles.incoming}`}>
      {!isOutgoing && renderAgentAvatar()}
      <div className={styles.bubble}>
        <div className={styles.bubbleHeader}>
          <span className={styles.author}>{authorName}</span>
          <span className={styles.time}>{time}</span>
          {hasContent && (
            <button
              type="button"
              className={styles.ttsBtn}
              onClick={handleTtsClick}
              title={isPlaying ? 'Остановить' : 'Воспроизвести'}
              aria-label={isPlaying ? 'Остановить воспроизведение' : 'Воспроизвести текст'}
            >
              {isPlaying ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              )}
            </button>
          )}
        </div>
        <p className={styles.content}>{message.content}</p>
      </div>
    </div>
  )
}
