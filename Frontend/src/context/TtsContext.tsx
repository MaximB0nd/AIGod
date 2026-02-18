/**
 * Глобальное состояние text-to-speech.
 * Использует нативный Web Speech API — бесплатно, без зависимостей, работает сразу.
 *
 * - Воспроизведение не останавливается при обновлении ленты
 * - При выборе другого сообщения — предыдущее останавливается, проигрывается новое
 * - После окончания сообщения автоматически проигрывается следующее в ленте
 */

import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from 'react'
import { useChat } from '@/context/ChatContext'
import type { FeedItem } from '@/types/chat'

interface TtsContextValue {
  playingMessageId: string | null
  ttsAvailable: boolean
  play: (messageId: string, text: string) => void
  stop: () => void
}

const TtsContext = createContext<TtsContextValue | null>(null)

/** Milena в конце — плохо говорит в Safari. Приоритет: Yuri, Katya, Irina, Google, Yandex */
const PREFERRED_RU_VOICES = ['Yuri', 'Katya', 'Microsoft Irina', 'Google русский', 'Yandex', 'Milena']

function getBestRussianVoice(): SpeechSynthesisVoice | null {
  const voices = speechSynthesis.getVoices()
  const ru = voices.filter((v) => v.lang.startsWith('ru'))
  if (ru.length === 0) return null
  const lower = (s: string) => s.toLowerCase()
  for (const name of PREFERRED_RU_VOICES) {
    const found = ru.find((v) => lower(v.name).includes(lower(name)) || lower(name).includes(lower(v.name)))
    if (found) return found
  }
  return ru[0]
}

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
  const [ttsAvailable, setTtsAvailable] = useState(false)
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null)
  const { feed } = useChat()
  const feedRef = useRef(feed)
  feedRef.current = feed

  useEffect(() => {
    if (!('speechSynthesis' in window)) return
    setTtsAvailable(true)
    const check = () => {
      voiceRef.current = getBestRussianVoice()
    }
    check()
    speechSynthesis.onvoiceschanged = check
    return () => {
      speechSynthesis.onvoiceschanged = null
    }
  }, [])

  const stop = useCallback(() => {
    speechSynthesis.cancel()
    setPlayingMessageId(null)
  }, [])

  const play = useCallback((messageId: string, text: string) => {
    const trimmed = text?.trim()
    if (!trimmed || !ttsAvailable) return

    speechSynthesis.cancel()
    setPlayingMessageId(messageId)

    const utterance = new SpeechSynthesisUtterance(trimmed)
    utterance.lang = 'ru-RU'
    utterance.rate = 0.92
    utterance.pitch = 0.92
    const voice = voiceRef.current ?? getBestRussianVoice()
    if (voice) utterance.voice = voice

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
  }, [ttsAvailable])

  return (
    <TtsContext.Provider value={{ playingMessageId, ttsAvailable, play, stop }}>
      {children}
    </TtsContext.Provider>
  )
}

export function useTts() {
  const ctx = useContext(TtsContext)
  if (!ctx) throw new Error('useTts must be used within TtsProvider')
  return ctx
}
