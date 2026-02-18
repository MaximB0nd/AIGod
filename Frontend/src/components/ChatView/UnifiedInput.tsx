/**
 * Единое поле ввода сообщений
 * — Без тегов: отправка всем агентам
 * — С одним @тегом: отправка конкретному агенту
 * — С несколькими тегами: отправка запрещена
 * — Автодополнение при вводе @
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type { Chat, Character } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import styles from './ChatView.module.css'

interface UnifiedInputProps {
  chat: Chat
}

/** Парсит @упоминания из текста и возвращает id агентов (без дубликатов) */
function parseMentions(
  text: string,
  characters: Character[],
  chatCharacterIds: string[]
): string[] {
  const mentionRegex = /@([^\s@]+)/g
  const matches = [...text.matchAll(mentionRegex)]
  const agentIds = new Set<string>()

  for (const m of matches) {
    const mention = m[1].toLowerCase()
    const chatChars = characters.filter((c) => chatCharacterIds.includes(c.id))
    const found = chatChars.find(
      (c) =>
        c.name.toLowerCase() === mention || c.name.toLowerCase().startsWith(mention)
    )
    if (found) agentIds.add(found.id)
  }
  return [...agentIds]
}

/** Проверяет, есть ли в тексте осмысленный контент (не только теги и пробелы) */
function hasMeaningfulText(text: string): boolean {
  const withoutMentions = text.replace(/@[^\s@]+/g, '').trim()
  return withoutMentions.length > 0
}

export function UnifiedInput({ chat }: UnifiedInputProps) {
  const { characters, sendMessage, sendMessageToRoom } = useChat()
  const [text, setText] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestions, setSuggestions] = useState<Character[]>([])
  const [suggestionIndex, setSuggestionIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const lastAtPos = useRef(-1)

  const chatCharacters = chat.characterIds
    .map((id) => characters.find((c) => c.id === id))
    .filter(Boolean) as Character[]

  const trimmed = text.trim()
  const agentIds = parseMentions(trimmed, characters, chat.characterIds)
  const hasMultipleMentions = agentIds.length > 1
  const hasMeaningful = hasMeaningfulText(trimmed)
  const canSend =
    trimmed.length > 0 &&
    hasMeaningful &&
    !hasMultipleMentions

  const handleSend = useCallback(async () => {
    const t = text.trim()
    if (!t) return
    if (!hasMeaningfulText(t)) return
    const ids = parseMentions(t, characters, chat.characterIds)
    if (ids.length > 1) return

    setError(null)
    try {
      if (ids.length === 1) {
        await sendMessage(chat.id, ids[0], t)
      } else {
        await sendMessageToRoom(chat.id, t)
      }
      setText('')
      setShowSuggestions(false)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Ошибка отправки'
      )
    }
  }, [text, chat.id, chat.characterIds, characters, sendMessage, sendMessageToRoom])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (showSuggestions) {
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          setSuggestionIndex((i) => Math.min(i + 1, suggestions.length - 1))
          return
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault()
          setSuggestionIndex((i) => Math.max(i - 1, 0))
          return
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault()
          if (suggestions[suggestionIndex]) {
            const before = text.slice(0, lastAtPos.current)
            const after = text.slice(inputRef.current?.selectionStart ?? text.length)
            const name = suggestions[suggestionIndex].name
            setText(`${before}@${name} ${after}`)
            setShowSuggestions(false)
            setTimeout(() => inputRef.current?.focus(), 0)
          }
          return
        }
        if (e.key === 'Escape') {
          setShowSuggestions(false)
          return
        }
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [showSuggestions, suggestions, suggestionIndex, text, handleSend]
  )

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value
      const cursorPos = e.target.selectionStart ?? value.length
      setText(value)

      const beforeCursor = value.slice(0, cursorPos)
      const atMatch = beforeCursor.match(/@([^\s@]*)$/)
      if (atMatch) {
        lastAtPos.current = cursorPos - atMatch[0].length
        const query = atMatch[1].toLowerCase()
        const filtered = chatCharacters.filter((c) =>
          c.name.toLowerCase().includes(query)
        )
        setSuggestions(filtered)
        setSuggestionIndex(0)
        setShowSuggestions(filtered.length > 0)
      } else {
        setShowSuggestions(false)
      }
    },
    [chatCharacters]
  )

  const handleSelectSuggestion = useCallback((char: Character) => {
    const before = text.slice(0, lastAtPos.current)
    const after = text.slice(inputRef.current?.selectionStart ?? text.length)
    setText(`${before}@${char.name} ${after}`)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }, [text])

  useEffect(() => {
    if (!showSuggestions) return
    const handler = (e: MouseEvent) => {
      if (!inputRef.current?.contains(e.target as Node)) setShowSuggestions(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showSuggestions])

  if (chatCharacters.length === 0) {
    return (
      <div className={styles.inputEmpty}>
        <p>Добавьте агентов в чат, чтобы отправлять сообщения</p>
      </div>
    )
  }

  const sendTitle =
    hasMultipleMentions
      ? 'Нельзя указывать несколько агентов — выберите одного или никого'
      : !hasMeaningful && trimmed
        ? 'Добавьте текст сообщения (не только тег)'
        : agentIds.length === 1
          ? `Отправить @${chatCharacters.find((c) => c.id === agentIds[0])?.name ?? 'агенту'}`
          : 'Отправить всем'

  return (
    <div className={styles.inputWrap}>
      {error && <p className={styles.inputError}>{error}</p>}
      <div className={styles.narratorInputContainer}>
        <input
          ref={inputRef}
          type="text"
          className={styles.input}
          placeholder="Сообщение... @имя — конкретному агенту, без тега — всем"
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
        />
        {showSuggestions && (
          <ul className={styles.mentionSuggestions}>
            {suggestions.map((c, i) => (
              <li
                key={c.id}
                className={`${styles.mentionItem} ${i === suggestionIndex ? styles.mentionItemActive : ''}`}
                onClick={() => handleSelectSuggestion(c)}
              >
                <span className={styles.mentionName}>@{c.name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <button
        type="button"
        className={styles.sendBtn}
        onClick={handleSend}
        disabled={!canSend}
        title={sendTitle}
      >
        ➤
      </button>
    </div>
  )
}
