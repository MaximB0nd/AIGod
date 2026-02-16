/**
 * Поле ввода сообщения
 * Позволяет выбрать персонажа и отправить сообщение от его имени
 */

import { useState, useCallback } from 'react'
import type { Chat } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import styles from './ChatView.module.css'

interface MessageInputProps {
  chat: Chat
}

export function MessageInput({ chat }: MessageInputProps) {
  const { characters, sendMessage } = useChat()
  const [text, setText] = useState('')
  const [selectedCharId, setSelectedCharId] = useState<string>(chat.characterIds[0] ?? '')

  const chatCharacters = chat.characterIds
    .map((id) => characters.find((c) => c.id === id))
    .filter(Boolean)

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed || !selectedCharId) return
    sendMessage(chat.id, selectedCharId, trimmed)
    setText('')
  }, [text, selectedCharId, chat.id, sendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  if (chatCharacters.length === 0) {
    return (
      <div className={styles.inputEmpty}>
        <p>Добавьте персонажа в чат, чтобы отправлять сообщения</p>
      </div>
    )
  }

  return (
    <div className={styles.inputWrap}>
      <select
        className={styles.charSelect}
        value={selectedCharId}
        onChange={(e) => setSelectedCharId(e.target.value)}
      >
        {chatCharacters.map((c) => (
          <option key={c!.id} value={c!.id}>
            {c!.name}
          </option>
        ))}
      </select>
      <input
        type="text"
        className={styles.input}
        placeholder="Сообщение от имени персонажа..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        className={styles.sendBtn}
        onClick={handleSend}
        disabled={!text.trim()}
        title="Отправить"
      >
        ➤
      </button>
    </div>
  )
}
