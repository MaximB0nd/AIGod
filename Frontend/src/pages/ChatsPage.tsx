/**
 * Главная страница — чаты нейросетей в стиле Telegram
 */

import { useState, useCallback } from 'react'
import { useChat } from '@/context/ChatContext'
import { ChatList } from '@/components/ChatList'
import { ChatView } from '@/components/ChatView'
import { CreateChatModal } from '@/components/CreateChatModal'
import { AddCharacterModal } from '@/components/AddCharacterModal'
import styles from './ChatsPage.module.css'

export function ChatsPage() {
  const { activeChat, isLoading, deleteChat } = useChat()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAddCharModal, setShowAddCharModal] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

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
    <div className={styles.layout}>
      <button
        type="button"
        className={styles.toggleBtn}
        onClick={() => setSidebarCollapsed((v) => !v)}
        title={sidebarCollapsed ? 'Развернуть панель' : 'Свернуть панель'}
        aria-label={sidebarCollapsed ? 'Развернуть панель' : 'Свернуть панель'}
      >
        {sidebarCollapsed ? '▶' : '◀'}
      </button>
      <div className={`${styles.sidebarWrapper} ${sidebarCollapsed ? styles.collapsed : ''}`}>
        <ChatList onCreateChat={() => setShowCreateModal(true)} />
      </div>
      <div className={`${styles.mainWrapper} ${sidebarCollapsed ? styles.mainExpanded : ''}`}>
        <ChatView
          onAddCharacter={activeChat ? handleAddCharacter : undefined}
          onDeleteChat={activeChat ? handleDeleteChat : undefined}
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
