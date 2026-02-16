/**
 * Главная страница — чаты нейросетей в стиле Telegram
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useChat } from '@/context/ChatContext'
import { ChatList } from '@/components/ChatList'
import { ChatView } from '@/components/ChatView'
import { CreateChatModal } from '@/components/CreateChatModal'
import { AddCharacterModal } from '@/components/AddCharacterModal'
import styles from './ChatsPage.module.css'

const SIDEBAR_MIN_WIDTH = 240
const SIDEBAR_MAX_WIDTH = 600
const SIDEBAR_DEFAULT_WIDTH = 360
const STORAGE_KEY = 'chats-sidebar-width'

function getStoredWidth(): number {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const w = parseInt(stored, 10)
      if (w >= SIDEBAR_MIN_WIDTH && w <= SIDEBAR_MAX_WIDTH) return w
    }
  } catch {
    /* ignore */
  }
  return SIDEBAR_DEFAULT_WIDTH
}

export function ChatsPage() {
  const { activeChat, isLoading, deleteChat } = useChat()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAddCharModal, setShowAddCharModal] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(getStoredWidth)
  const [isResizing, setIsResizing] = useState(false)
  const widthRef = useRef(sidebarWidth)
  widthRef.current = sidebarWidth

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMove = (e: MouseEvent) => {
      const newWidth = Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, e.clientX))
      setSidebarWidth(newWidth)
    }

    const handleUp = () => {
      setIsResizing(false)
      try {
        localStorage.setItem(STORAGE_KEY, String(widthRef.current))
      } catch {
        /* ignore */
      }
    }

    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
  }, [isResizing])

  const handleAddCharacter = useCallback(() => {
    setShowAddCharModal(true)
  }, [])

  const handleDeleteChat = useCallback(async () => {
    if (!activeChat) return
    if (window.confirm(`Удалить чат «${activeChat.title}»?`)) {
      await deleteChat(activeChat.id)
    }
  }, [activeChat, deleteChat])

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <p>Загрузка чатов...</p>
      </div>
    )
  }

  return (
    <div className={`${styles.layout} ${isResizing ? styles.resizing : ''}`}>
      <div
        className={`${styles.sidebarWrapper} ${sidebarCollapsed ? styles.collapsed : ''} ${isResizing ? styles.resizing : ''}`}
        style={sidebarCollapsed ? undefined : { width: sidebarWidth, minWidth: sidebarWidth }}
      >
        <ChatList onCreateChat={() => setShowCreateModal(true)} />
      </div>
      {!sidebarCollapsed && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Изменить ширину панели"
          className={styles.resizeHandle}
          onMouseDown={handleResizeStart}
        />
      )}
      <div className={styles.mainWrapper}>
        <ChatView
          onAddCharacter={activeChat ? handleAddCharacter : undefined}
          onDeleteChat={activeChat ? handleDeleteChat : undefined}
          onToggleSidebar={() => setSidebarCollapsed((v) => !v)}
          sidebarCollapsed={sidebarCollapsed}
        />
      </div>
      <CreateChatModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
      <AddCharacterModal
        isOpen={showAddCharModal}
        chat={activeChat}
        onClose={() => setShowAddCharModal(false)}
      />
    </div>
  )
}
