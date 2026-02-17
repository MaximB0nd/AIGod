/**
 * Глобальное состояние text-to-speech.
 * Воспроизведение не останавливается при обновлении ленты (новые сообщения).
 * При выборе другого сообщения — предыдущее останавливается, проигрывается новое.
 * После окончания сообщения автоматически проигрывается следующее в ленте.
 */

import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react'
import { useChat } from '@/context/ChatContext'
import type { FeedItem } from '@/types/chat'

interface TtsContextValue {
  playingMessageId: string | null
  play: (messageId: string, text: string) => void
  stop: () => void
}

const TtsContext = createContext<TtsContextValue | null>(null)

function getNextMessage(feed: FeedItem[], currentMessageId: string): { id: string; text: string } | null {
  const messageItems = feed.filter(
    (x): x is FeedItem & { type: 'message' } =>
      x.type === 'message' && Boolean((x.data as { content?: string }).content?.trim())
  )
  const idx = messageItems.findIndex((x) => x.data.id === currentMessageId)
  if (idx < 0 || idx >= messageItems.length - 1) return null
  const next = messageItems[idx + 1]
  const content = (next.data as { content?: string }).content ?? ''
  return content.trim() ? { id: next.data.id, text: content } : null
}

export function TtsProvider({ children }: { children: ReactNode }) {
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null)
  const { feed } = useChat()
  const feedRef = useRef(feed)
  feedRef.current = feed

  const stop = useCallback(() => {
    speechSynthesis.cancel()
    setPlayingMessageId(null)
  }, [])

  const play = useCallback((messageId: string, text: string) => {
    const trimmed = text?.trim()
    if (!trimmed) return

    speechSynthesis.cancel()
    setPlayingMessageId(messageId)

    const utterance = new SpeechSynthesisUtterance(trimmed)
    utterance.lang = 'ru-RU'
    utterance.rate = 0.95
    utterance.onend = () => {
      const next = getNextMessage(feedRef.current, messageId)
      if (next) {
        play(next.id, next.text)
      } else {
        setPlayingMessageId(null)
      }
    }
    utterance.onerror = () => setPlayingMessageId(null)
    speechSynthesis.speak(utterance)
  }, [])

  return (
    <TtsContext.Provider value={{ playingMessageId, play, stop }}>
      {children}
    </TtsContext.Provider>
  )
}

export function useTts() {
  const ctx = useContext(TtsContext)
  if (!ctx) throw new Error('useTts must be used within TtsProvider')
  return ctx
}
