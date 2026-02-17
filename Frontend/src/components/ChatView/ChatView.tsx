/**
 * Окно чата — нейросети общаются, пользователь пишет события от рассказчика
 */

import { useRef, useEffect, useCallback, useState } from 'react'
import { useChat } from '@/context/ChatContext'
import { MessageBubble } from './MessageBubble'
import { EventBubble } from './EventBubble'
import { ChatHeader } from './ChatHeader'
import { NarratorInput } from './NarratorInput'
import { GroupInfoModal } from '../GroupInfoModal/GroupInfoModal'
import styles from './ChatView.module.css'

interface ChatViewProps {
  onAddCharacter?: () => void
  onToggleSidebar?: () => void
  sidebarCollapsed?: boolean
  onToggleRightPanel?: () => void
  rightPanelCollapsed?: boolean
}

export function ChatView({ onAddCharacter, onToggleSidebar, sidebarCollapsed, onToggleRightPanel, rightPanelCollapsed }: ChatViewProps) {
  const { activeChat, feed, characters, selectChat, isMessagesLoading } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showGroupInfo, setShowGroupInfo] = useState(false)

  const handleCloseChat = useCallback(() => {
    selectChat(null)
  }, [selectChat])

  const handleGroupClick = useCallback(() => {
    setShowGroupInfo(true)
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [feed])

  if (!activeChat) {
    return (
      <div className={styles.chat}>
        {(onToggleSidebar || onToggleRightPanel) && (
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
            <div className={styles.headerActions} style={{ marginLeft: 'auto' }}>
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
        )}
        <div className={styles.empty}>
          <div className={styles.emptyContent}>
          <p>Выберите чат или создайте новый</p>
          <span>Нейросети общаются, вы — рассказчик событий</span>
        </div>
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
        onToggleSidebar={onToggleSidebar}
        sidebarCollapsed={sidebarCollapsed}
        onToggleRightPanel={onToggleRightPanel}
        rightPanelCollapsed={rightPanelCollapsed}
        onGroupClick={handleGroupClick}
      />
      <div className={styles.messages} ref={scrollRef}>
        <div className={styles.messagesInner}>
          {isMessagesLoading && (
            <div className={styles.loading}>
              <span className={styles.loadingSpinner} />
              <p>Загрузка ленты...</p>
            </div>
          )}
          {!isMessagesLoading &&
            feed.map((item) =>
              item.type === 'message' ? (
                <MessageBubble
                  key={item.data.id}
                  message={item.data}
                  character={getCharacter(item.data.characterId)}
                  isOutgoing={false}
                />
              ) : (
                <EventBubble key={item.data.id} event={item.data} characters={characters} />
              )
            )}
        </div>
      </div>
      <NarratorInput chat={activeChat} />
      <GroupInfoModal
        isOpen={showGroupInfo}
        onClose={() => setShowGroupInfo(false)}
        chat={activeChat}
      />
    </div>
  )
}
