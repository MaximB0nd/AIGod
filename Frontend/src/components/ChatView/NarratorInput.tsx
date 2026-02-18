/**
 * Поле ввода событий от рассказчика
 * События адресуются всем агентам или выбранным через @mention
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import type { Chat, Character } from '@/types/chat'
import { useChat } from '@/context/ChatContext'
import { ApiError } from '@/api/client'
import styles from './ChatView.module.css'

interface NarratorInputProps {
  chat: Chat
}

/** Парсит @упоминания из текста и возвращает id агентов (без дубликатов) */
function parseMentions(text: string, characters: Character[], chatCharacterIds: string[]): string[] {
  const mentionRegex = /@([^\s@]+)/g
  const matches = [...text.matchAll(mentionRegex)]
  const agentIds = new Set<string>()

  for (const m of matches) {
    const mention = m[1].toLowerCase()
    const chatChars = characters.filter((c) => chatCharacterIds.includes(c.id))
    const found = chatChars.find(
      (c) => c.name.toLowerCase() === mention || c.name.toLowerCase().startsWith(mention)
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

/** Проверяет, тегнут ли один и тот же агент несколько раз */
function hasDuplicateAgentMention(
  text: string,
  characters: Character[],
  chatCharacterIds: string[]
): boolean {
  const mentionRegex = /@([^\s@]+)/g
  const matches = [...text.matchAll(mentionRegex)]
  const chatChars = characters.filter((c) => chatCharacterIds.includes(c.id))
  const resolvedIds: string[] = []
  for (const m of matches) {
    const mention = m[1].toLowerCase()
    const found = chatChars.find(
      (c) => c.name.toLowerCase() === mention || c.name.toLowerCase().startsWith(mention)
    )
    if (found) resolvedIds.push(found.id)
  }
  return resolvedIds.length !== new Set(resolvedIds).size
}

export function NarratorInput({ chat }: NarratorInputProps) {
  const { characters, sendEvent } = useChat()
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
  const hasDuplicates = hasDuplicateAgentMention(trimmed, characters, chat.characterIds)
  const canSend =
    trimmed.length > 0 &&
    hasMeaningfulText(trimmed) &&
    !hasDuplicates

  const handleSend = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed) return
    if (!hasMeaningfulText(trimmed)) return
    if (hasDuplicateAgentMention(trimmed, characters, chat.characterIds)) return

    setError(null)
    const agentIds = parseMentions(trimmed, characters, chat.characterIds)
    try {
      await sendEvent(chat.id, trimmed, agentIds)
      setText('')
      setShowSuggestions(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Ошибка отправки события')
    }
  }, [text, chat.id, chat.characterIds, characters, sendEvent])

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
        const filtered = chatCharacters.filter((c) => c.name.toLowerCase().includes(query))
        setSuggestions(filtered)
        setSuggestionIndex(0)
        setShowSuggestions(filtered.length > 0)
      } else {
        setShowSuggestions(false)
      }
    },
    [chatCharacters]
  )

  const handleSelectSuggestion = useCallback(
    (char: Character) => {
      const before = text.slice(0, lastAtPos.current)
      const after = text.slice(inputRef.current?.selectionStart ?? text.length)
      setText(`${before}@${char.name} ${after}`)
      setShowSuggestions(false)
      inputRef.current?.focus()
    },
    [text]
  )

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
        <p>Добавьте агентов в чат, чтобы описывать события</p>
      </div>
    )
  }

  return (
    <div className={styles.inputWrap}>
      {error && <p className={styles.inputError}>{error}</p>}
      <div className={styles.narratorInputContainer}>
        <input
          ref={inputRef}
          type="text"
          className={styles.input}
          placeholder="Опишите событие... @имя — для конкретного агента"
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
        title={
          !hasMeaningfulText(trimmed) && trimmed
            ? 'Добавьте описание события (не только тег)'
            : hasDuplicates
              ? 'Нельзя указывать одного агента несколько раз'
              : 'Отправить событие'
        }
      >
        →
      </button>
    </div>
  )
}
