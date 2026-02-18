/**
 * Окно чата — нейросети общаются, пользователь пишет события от рассказчика
 */

import { useRef, useEffect, useLayoutEffect, useCallback, useState } from 'react'
import { useChat } from '@/context/ChatContext'
import { MessageBubble } from './MessageBubble'
import { EventBubble } from './EventBubble'
import { ChatHeader } from './ChatHeader'
import { UnifiedInput } from './UnifiedInput'
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
  const {
    activeChat,
    feed,
    characters,
    selectChat,
    isMessagesLoading,
    hasMoreMessages,
    isLoadMoreLoading,
    loadMoreMessages,
  } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)
  const loadMoreSentinelRef = useRef<HTMLDivElement>(null)
  const prevFeedLengthRef = useRef(0)
  const [showGroupInfo, setShowGroupInfo] = useState(false)

  const handleCloseChat = useCallback(() => {
    selectChat(null)
  }, [selectChat])

  const handleGroupClick = useCallback(() => {
    setShowGroupInfo(true)
  }, [])

  // Скролл вниз при загрузке/обновлении ленты. Двойной rAF нужен, чтобы дождаться
  // завершения layout — иначе scrollHeight может быть 0 и контент не отображается до первой прокрутки.
  useLayoutEffect(() => {
    const container = scrollRef.current
    if (!container || feed.length === 0) return

    const scrollToBottom = () => {
      container.scrollTop = container.scrollHeight
    }

    let raf2: number | null = null
    let fallbackId: ReturnType<typeof setTimeout> | null = null
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        scrollToBottom()
        // Fallback: на медленных устройствах layout может завершиться позже
        fallbackId = setTimeout(scrollToBottom, 100)
      })
    })
    return () => {
      cancelAnimationFrame(raf1)
      if (raf2 != null) cancelAnimationFrame(raf2)
      if (fallbackId != null) clearTimeout(fallbackId)
    }
  }, [feed, isMessagesLoading])

  const scrollHeightBeforeLoadRef = useRef(0)
  useEffect(() => {
    if (isLoadMoreLoading) {
      scrollHeightBeforeLoadRef.current = scrollRef.current?.scrollHeight ?? 0
    }
  }, [isLoadMoreLoading])

  useEffect(() => {
    if (!isLoadMoreLoading && prevFeedLengthRef.current > 0 && feed.length > prevFeedLengthRef.current) {
      const container = scrollRef.current
      if (container && scrollHeightBeforeLoadRef.current > 0) {
        const delta = container.scrollHeight - scrollHeightBeforeLoadRef.current
        if (delta > 0) container.scrollTop += delta
      }
    }
    prevFeedLengthRef.current = feed.length
  }, [feed.length, isLoadMoreLoading])

  useEffect(() => {
    const sentinel = loadMoreSentinelRef.current
    const container = scrollRef.current
    if (!sentinel || !container || !hasMoreMessages || isLoadMoreLoading) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          loadMoreMessages()
        }
      },
      { root: container, rootMargin: '100px', threshold: 0 }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMoreMessages, isLoadMoreLoading, loadMoreMessages])

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
          {hasMoreMessages && (
            <div ref={loadMoreSentinelRef} className={styles.loadMoreSentinel}>
              {isLoadMoreLoading ? (
                <span className={styles.loadingSpinner} />
              ) : (
                <span className={styles.loadMoreHint}>Потяните вверх для загрузки</span>
              )}
            </div>
          )}
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
                  character={item.data.sender === 'user' ? undefined : getCharacter(item.data.characterId)}
                  isOutgoing={item.data.sender === 'user'}
                />
              ) : (
                <EventBubble key={item.data.id} event={item.data} characters={characters} />
              )
            )}
        </div>
      </div>
      <UnifiedInput chat={activeChat} />
      <GroupInfoModal
        isOpen={showGroupInfo}
        onClose={() => setShowGroupInfo(false)}
        chat={activeChat}
      />
    </div>
  )
}
