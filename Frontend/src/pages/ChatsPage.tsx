/**
 * Главная страница — комнаты в стиле Telegram
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { ChatList } from '@/components/ChatList'
import { ChatView } from '@/components/ChatView'
import { CreateChatModal } from '@/components/CreateChatModal'
import { AddCharacterModal } from '@/components/AddCharacterModal'
import { RelationshipsGraph } from '@/components/RelationshipsGraph'
import { STORAGE_KEYS } from '@/utils/storage'
import styles from './ChatsPage.module.css'

/* Минимум: логотип + кнопка «+» + компактный выход */
const SIDEBAR_MIN_WIDTH = 200
const SIDEBAR_MAX_WIDTH = 600
const SIDEBAR_DEFAULT_WIDTH = 360
const STORAGE_KEY = STORAGE_KEYS.SIDEBAR_WIDTH

const RIGHT_PANEL_MIN_WIDTH = 240
const RIGHT_PANEL_MAX_WIDTH = 600
const RIGHT_PANEL_DEFAULT_WIDTH = 320
const RIGHT_STORAGE_KEY = STORAGE_KEYS.RIGHT_PANEL_WIDTH

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

function getStoredRightWidth(): number {
  try {
    const stored = localStorage.getItem(RIGHT_STORAGE_KEY)
    if (stored) {
      const w = parseInt(stored, 10)
      if (w >= RIGHT_PANEL_MIN_WIDTH && w <= RIGHT_PANEL_MAX_WIDTH) return w
    }
  } catch {
    /* ignore */
  }
  return RIGHT_PANEL_DEFAULT_WIDTH
}

export function ChatsPage() {
  const { activeChat, isLoading, deleteChat, refreshChatsSilent } = useChat()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAddCharModal, setShowAddCharModal] = useState(false)
  const [chatForAddModal, setChatForAddModal] = useState<Chat | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const prevSidebarCollapsedRef = useRef(sidebarCollapsed)
  const [sidebarWidth, setSidebarWidth] = useState(getStoredWidth)
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(true)
  const [rightPanelWidth, setRightPanelWidth] = useState(getStoredRightWidth)
  const [resizingSide, setResizingSide] = useState<'left' | 'right' | null>(null)
  const widthRef = useRef(sidebarWidth)
  const rightWidthRef = useRef(rightPanelWidth)
  widthRef.current = sidebarWidth
  rightWidthRef.current = rightPanelWidth

  const handleResizeStartLeft = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setResizingSide('left')
  }, [])

  const handleResizeStartRight = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setResizingSide('right')
  }, [])

  useEffect(() => {
    if (resizingSide !== 'left') return

    const handleMove = (e: MouseEvent) => {
      const newWidth = Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, e.clientX))
      setSidebarWidth(newWidth)
    }

    const handleUp = () => {
      setResizingSide(null)
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
  }, [resizingSide])

  useEffect(() => {
    if (resizingSide !== 'right') return

    const handleMove = (e: MouseEvent) => {
      const widthFromRight = window.innerWidth - e.clientX - 16
      const newWidth = Math.max(
        RIGHT_PANEL_MIN_WIDTH,
        Math.min(RIGHT_PANEL_MAX_WIDTH, widthFromRight)
      )
      setRightPanelWidth(newWidth)
    }

    const handleUp = () => {
      setResizingSide(null)
      try {
        localStorage.setItem(RIGHT_STORAGE_KEY, String(rightWidthRef.current))
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
  }, [resizingSide])

  const handleAddCharacter = useCallback(() => {
    setChatForAddModal(null)
    setShowAddCharModal(true)
  }, [])

  const handleAddCharacterForChat = useCallback((chat: Chat) => {
    setChatForAddModal(chat)
    setShowAddCharModal(true)
  }, [])

  const handleDeleteChatFromList = useCallback(
    async (chat: Chat) => {
      if (!window.confirm(`Удалить чат «${chat.title}»?`)) return
      try {
        await deleteChat(chat.id)
      } catch {
        window.alert('Не удалось удалить чат. Попробуйте позже.')
      }
    },
    [deleteChat]
  )

  const handleCloseAddCharModal = useCallback(() => {
    setShowAddCharModal(false)
    setChatForAddModal(null)
  }, [])

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      if (prev) setRightPanelCollapsed(true)
      return !prev
    })
  }, [])

  useEffect(() => {
    refreshChatsSilent()
  }, [refreshChatsSilent])

  useEffect(() => {
    if (prevSidebarCollapsedRef.current && !sidebarCollapsed) {
      refreshChatsSilent()
    }
    prevSidebarCollapsedRef.current = sidebarCollapsed
  }, [sidebarCollapsed, refreshChatsSilent])

  const handleToggleRightPanel = useCallback(() => {
    setRightPanelCollapsed((prev) => {
      if (prev) setSidebarCollapsed(true)
      return !prev
    })
  }, [])

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <p>Загрузка чатов...</p>
      </div>
    )
  }

  return (
    <div className={`${styles.layout} ${resizingSide ? styles.resizing : ''}`}>
      <div
        className={`${styles.sidebarWrapper} ${sidebarCollapsed ? styles.collapsed : ''} ${resizingSide === 'left' ? styles.resizing : ''}`}
        style={sidebarCollapsed ? undefined : { width: sidebarWidth, minWidth: sidebarWidth }}
      >
        <ChatList
          onCreateChat={() => setShowCreateModal(true)}
          onDeleteChat={handleDeleteChatFromList}
          onAddCharacter={handleAddCharacterForChat}
        />
      </div>
      {!sidebarCollapsed && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Изменить ширину левой панели"
          className={styles.resizeHandle}
          onMouseDown={handleResizeStartLeft}
        />
      )}
      <div className={styles.mainWrapper}>
        <ChatView
          onAddCharacter={activeChat ? handleAddCharacter : undefined}
          onToggleSidebar={handleToggleSidebar}
          sidebarCollapsed={sidebarCollapsed}
          onToggleRightPanel={handleToggleRightPanel}
          rightPanelCollapsed={rightPanelCollapsed}
        />
      </div>
      {!rightPanelCollapsed && (
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Изменить ширину правой панели"
          className={styles.resizeHandle}
          onMouseDown={handleResizeStartRight}
        />
      )}
      <div
        className={`${styles.rightPanelWrapper} ${rightPanelCollapsed ? styles.rightPanelCollapsed : ''} ${resizingSide === 'right' ? styles.resizing : ''}`}
        style={rightPanelCollapsed ? undefined : { width: rightPanelWidth, minWidth: rightPanelWidth }}
      >
        <div className={styles.rightPanel}>
          <RelationshipsGraph
            roomId={activeChat?.id ?? null}
            onPanelOpen={!rightPanelCollapsed}
          />
        </div>
      </div>
      <CreateChatModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
      <AddCharacterModal
        isOpen={showAddCharModal}
        chat={chatForAddModal ?? activeChat}
        onClose={handleCloseAddCharModal}
      />
    </div>
  )
}
