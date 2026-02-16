/**
 * Отображение события от рассказчика
 */

import type { Event, Character } from '@/types/chat'
import { formatChatTime } from '@/utils/format'
import styles from './ChatView.module.css'

interface EventBubbleProps {
  event: Event
  characters: Character[]
}

export function EventBubble({ event, characters }: EventBubbleProps) {
  const time = formatChatTime(event.timestamp)
  const isBroadcast = event.agentIds.length === 0
  const targetNames = event.agentIds
    .map((id) => characters.find((c) => c.id === id)?.name)
    .filter(Boolean)

  return (
    <div className={styles.eventWrap}>
      <div className={styles.eventBubble}>
        <div className={styles.eventMeta}>
          <span className={styles.eventLabel}>Событие</span>
          <span className={styles.time}>{time}</span>
        </div>
        <p className={styles.eventDescription}>{event.description}</p>
        {!isBroadcast && targetNames.length > 0 && (
          <span className={styles.eventTargets}>→ {targetNames.join(', ')}</span>
        )}
      </div>
    </div>
  )
}
