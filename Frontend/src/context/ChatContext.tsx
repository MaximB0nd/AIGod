/**
 * Контекст комнат
 * Подключён к бэкенду (Room/Agent)
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { Chat, Message, Character, FeedItem } from '@/types/chat'
import { isHiddenSystemMessage, filterVisibleFeed } from '@/utils/feedFilter'
import type { DefaultAgentSummary } from '@/api/agents'
import * as chatApi from '@/api/chat'
import { useRoomStream, type StreamMessage } from '@/hooks/useRoomStream'

interface ChatContextValue {
  chats: Chat[]
  characters: Character[]
  /** Шаблоны агентов с бэкенда (GET /api/default-agents) */
  defaultAgents: DefaultAgentSummary[]
  activeChat: Chat | null
  messages: Message[]
  feed: FeedItem[]
  isLoading: boolean
  isMessagesLoading: boolean
  /** Есть ли ещё сообщения для подгрузки при скролле вверх */
  hasMoreMessages: boolean
  /** Идёт ли подгрузка старых сообщений */
  isLoadMoreLoading: boolean
  selectChat: (chat: Chat | null) => void
  createChat: (data: { title: string; description?: string; orchestration_type?: 'single' | 'circular' | 'narrator' | 'full_context' }) => Promise<Chat>
  addCharacterToChat: (chatId: string, defaultAgentId: number) => Promise<void>
  createAgentToChat: (chatId: string, data: { name: string; character: string; avatar?: string }) => Promise<void>
  removeCharacterFromChat: (chatId: string, agentId: string) => Promise<void>
  sendMessage: (chatId: string, agentId: string, content: string) => Promise<void>
  sendMessageToRoom: (chatId: string, content: string) => Promise<void>
  sendEvent: (chatId: string, description: string, agentIds?: string[]) => Promise<void>
  /** Подгрузить более старые сообщения при скролле вверх */
  loadMoreMessages: () => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  refreshChats: () => Promise<void>
  /** Обновить чаты в фоне без индикатора загрузки */
  refreshChatsSilent: () => Promise<void>
  /** Уведомить об изменении скорости комнаты (для синхронизации с правой панелью) */
  updateRoomSpeedFromExternal: (roomId: string, speed: number) => void
  /** Последнее обновление скорости (roomId, speed) — для подписки в RelationshipsGraph */
  lastRoomSpeedUpdate: { roomId: string; speed: number } | null
}

const ChatContext = createContext<ChatContextValue | null>(null)

function sortFeed(a: FeedItem, b: FeedItem) {
  const ta = a.type === 'message' ? a.data.timestamp : a.data.timestamp
  const tb = b.type === 'message' ? b.data.timestamp : b.data.timestamp
  return new Date(ta).getTime() - new Date(tb).getTime()
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [defaultAgents, setDefaultAgents] = useState<DefaultAgentSummary[]>([])
  const [activeChat, setActiveChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [feed, setFeed] = useState<FeedItem[]>([])
  const [hasMoreMessages, setHasMoreMessages] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)
  const [isLoadMoreLoading, setIsLoadMoreLoading] = useState(false)
  const [lastRoomSpeedUpdate, setLastRoomSpeedUpdate] = useState<{ roomId: string; speed: number } | null>(null)
  /** Текущий активный чат — для проверки при завершении асинхронной загрузки (избегаем race condition) */
  const activeChatIdRef = useRef<string | null>(null)
  activeChatIdRef.current = activeChat?.id ?? null

  const updateRoomSpeedFromExternal = useCallback((roomId: string, speed: number) => {
    setLastRoomSpeedUpdate({ roomId, speed })
  }, [])

  useEffect(() => {
    chatApi.fetchDefaultAgents().then(setDefaultAgents).catch(() => setDefaultAgents([]))
  }, [])

  const loadChats = useCallback(async () => {
    setIsLoading(true)
    try {
      const chatsData = await chatApi.fetchChats()
      setChats(chatsData)
    } catch (err) {
      console.error('Failed to load chats:', err)
      setChats([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  const refreshChatsSilent = useCallback(async () => {
    try {
      const chatsData = await chatApi.fetchChats()
      setChats(chatsData)
    } catch (err) {
      console.error('Failed to refresh chats:', err)
    }
  }, [])

  const loadMessages = useCallback(async (chatId: string) => {
    setIsMessagesLoading(true)
    setHasMoreMessages(true)
    try {
      const { messages: msgs, feed: feedItems, characters: agents } =
        await chatApi.fetchMessagesFeedAndCharacters(chatId)
      // Применяем результат только если пользователь не переключился на другой чат
      if (activeChatIdRef.current === chatId) {
        setMessages(msgs)
        setFeed(filterVisibleFeed(feedItems).sort(sortFeed))
        setCharacters(agents)
        setHasMoreMessages(true)
      }
    } catch (err) {
      console.error('Failed to load messages:', err)
      if (activeChatIdRef.current === chatId) {
        setMessages([])
        setFeed([])
        setCharacters([])
        setHasMoreMessages(false)
      }
    } finally {
      if (activeChatIdRef.current === chatId) {
        setIsMessagesLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    loadChats()
  }, [loadChats])

  useEffect(() => {
    if (activeChat) {
      // Сразу очищаем при смене чата, чтобы не показывать сообщения из предыдущего
      setMessages([])
      setFeed([])
      setCharacters([])
      loadMessages(activeChat.id)
    } else {
      setMessages([])
      setFeed([])
      setCharacters([])
    }
  }, [activeChat?.id, loadMessages])

  const handleStreamMessage = useCallback(
    (msg: StreamMessage) => {
      if (!activeChat) return
      if (msg.type === 'message' && msg.payload) {
        const p = msg.payload as {
          id?: string | number
          text?: string
          /** Имя агента, 'user', или спецтип: 🎭 Рассказчик, 📊 Суммаризатор, Система */
          sender?: 'user' | 'agent' | 'system' | string
          agentId?: string | null
          timestamp?: string
        }
        const id = p.id != null ? String(p.id) : null
        const text = p.text ?? ''
        const timestamp = p.timestamp ?? new Date().toISOString()
        if (id) {
          const sender = p.sender ?? 'agent'
          if (isHiddenSystemMessage(sender)) return
          const newItem: FeedItem = {
            type: 'message',
            data: {
              id,
              chatId: activeChat.id,
              characterId: p.agentId != null ? String(p.agentId) : '',
              content: text,
              timestamp,
              isRead: true,
              sender,
            },
          }
          setFeed((prev) => {
            const exists = prev.some((x) => x.type === 'message' && String(x.data.id) === id)
            if (exists) return prev
            return [...prev, newItem].sort(sortFeed)
          })
          return
        }
      }
      if (msg.type === 'event' && msg.payload) {
        const p = msg.payload as {
          id?: string
          eventType?: string
          agentIds?: string[]
          description?: string
          timestamp?: string
        }
        if (p.id != null && p.timestamp != null) {
          const newItem: FeedItem = {
            type: 'event',
            data: {
              id: p.id,
              chatId: activeChat.id,
              type: p.eventType ?? 'user_event',
              description: p.description ?? '',
              agentIds: p.agentIds ?? [],
              timestamp: p.timestamp,
            },
          }
          setFeed((prev) => {
            const exists = prev.some((x) => x.type === 'event' && x.data.id === p.id)
            if (exists) return prev
            return [...prev, newItem].sort(sortFeed)
          })
          return
        }
      }
      // Fallback: полный reload при неполных данных
      if (msg.type === 'event' || msg.type === 'message') {
        loadMessages(activeChat.id)
      }
    },
    [activeChat, loadMessages]
  )

  useRoomStream({
    roomId: activeChat?.id ?? null,
    onMessage: handleStreamMessage,
    enabled: !!activeChat,
    onReconnect: (roomId) => loadMessages(roomId),
  })

  const selectChat = useCallback((chat: Chat | null) => {
    setActiveChat(chat)
  }, [])

  const createChat = useCallback(async (data: { title: string; description?: string; orchestration_type?: 'single' | 'circular' | 'narrator' | 'full_context' }) => {
    const chat = await chatApi.createChat(data)
    const chatsData = await chatApi.fetchChats()
    setChats(chatsData)
    const updated = chatsData.find((c) => c.id === chat.id) ?? chat
    setActiveChat(updated)
    return updated
  }, [])

  const addCharacterToChat = useCallback(
    async (chatId: string, defaultAgentId: number) => {
      await chatApi.addCharacterToChat(chatId, defaultAgentId)
      const chatsData = await chatApi.fetchChats()
      setChats(chatsData)
      if (activeChat?.id === chatId) {
        setActiveChat(chatsData.find((c) => c.id === chatId) ?? null)
        await loadMessages(chatId)
      }
    },
    [activeChat?.id, loadMessages]
  )

  const createAgentToChat = useCallback(
    async (chatId: string, data: { name: string; character: string; avatar?: string }) => {
      await chatApi.createAgentInChat(chatId, data)
      const chatsData = await chatApi.fetchChats()
      setChats(chatsData)
      if (activeChat?.id === chatId) {
        setActiveChat(chatsData.find((c) => c.id === chatId) ?? null)
        await loadMessages(chatId)
      }
    },
    [activeChat?.id, loadMessages]
  )

  const removeCharacterFromChat = useCallback(
    async (chatId: string, agentId: string) => {
      await chatApi.removeCharacterFromChat(chatId, agentId)
      const chatsData = await chatApi.fetchChats()
      setChats(chatsData)
      if (activeChat?.id === chatId) {
        setActiveChat(chatsData.find((c) => c.id === chatId) ?? null)
        await loadMessages(chatId)
      }
    },
    [activeChat?.id, loadMessages]
  )

  const sendMessage = useCallback(
    async (chatId: string, agentId: string, content: string) => {
      const msg = await chatApi.sendMessage(chatId, agentId, content)
      setFeed((prev) => {
        const newItem: FeedItem = {
          type: 'message',
          data: {
            id: msg.id,
            chatId,
            characterId: agentId,
            content: msg.content,
            timestamp: msg.timestamp,
            isRead: false,
            sender: 'user',
          },
        }
        const exists = prev.some((x) => x.type === 'message' && x.data.id === msg.id)
        if (exists) return prev
        return [...prev, newItem].sort(sortFeed)
      })
    },
    []
  )

  const sendMessageToRoom = useCallback(
    async (chatId: string, content: string) => {
      const msg = await chatApi.sendMessageToRoom(chatId, content)
      setFeed((prev) => {
        const newItem: FeedItem = {
          type: 'message',
          data: {
            id: msg.id,
            chatId,
            characterId: '',
            content: msg.content,
            timestamp: msg.timestamp,
            isRead: false,
            sender: 'user',
          },
        }
        const exists = prev.some((x) => x.type === 'message' && x.data.id === msg.id)
        if (exists) return prev
        return [...prev, newItem].sort(sortFeed)
      })
    },
    []
  )

  const sendEvent = useCallback(
    async (chatId: string, description: string, agentIds: string[] = []) => {
      const evt = await chatApi.sendEvent(chatId, description, agentIds)
      setFeed((prev) => {
        const newItem: FeedItem = {
          type: 'event',
          data: {
            id: evt.id,
            chatId,
            type: evt.type,
            description: evt.description,
            agentIds: evt.agentIds,
            timestamp: evt.timestamp,
          },
        }
        const exists = prev.some((x) => x.type === 'event' && x.data.id === evt.id)
        if (exists) return prev
        return [...prev, newItem].sort(sortFeed)
      })
    },
    []
  )

  const loadMoreMessages = useCallback(async () => {
    if (!activeChat || isLoadMoreLoading || !hasMoreMessages) return
    const oldestMessage = feed
      .filter((x): x is FeedItem & { type: 'message' } => x.type === 'message')
      .sort((a, b) => new Date(a.data.timestamp).getTime() - new Date(b.data.timestamp).getTime())[0]
    if (!oldestMessage) return

    setIsLoadMoreLoading(true)
    try {
      const { items, hasMore } = await chatApi.fetchOlderMessages(
        activeChat.id,
        oldestMessage.data.id,
        20
      )
      setHasMoreMessages(hasMore)
      setFeed((prev) => [...filterVisibleFeed(items), ...prev].sort(sortFeed))
    } catch (err) {
      console.error('Failed to load more messages:', err)
      setHasMoreMessages(false)
    } finally {
      setIsLoadMoreLoading(false)
    }
  }, [activeChat, feed, isLoadMoreLoading, hasMoreMessages])

  const deleteChat = useCallback(async (chatId: string) => {
    await chatApi.deleteChat(chatId)
    const chatsData = await chatApi.fetchChats()
    setChats(chatsData)
    if (activeChat?.id === chatId) setActiveChat(null)
  }, [activeChat?.id])

  const value: ChatContextValue = {
    chats,
    characters,
    defaultAgents,
    activeChat,
    messages,
    feed,
    isLoading,
    isMessagesLoading,
    hasMoreMessages,
    isLoadMoreLoading,
    selectChat,
    createChat,
    addCharacterToChat,
    createAgentToChat,
    removeCharacterFromChat,
    sendMessage,
    sendMessageToRoom,
    sendEvent,
    loadMoreMessages,
    deleteChat,
    refreshChats: loadChats,
    refreshChatsSilent,
    updateRoomSpeedFromExternal,
    lastRoomSpeedUpdate,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
