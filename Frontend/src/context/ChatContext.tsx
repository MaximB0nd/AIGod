/**
 * Контекст чатов нейросетей
 * Подключён к бэкенду (Room/Agent)
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { Chat, Message, Character, Event, FeedItem } from '@/types/chat'
import type { CharacterPreset } from '@/constants/characterPresets'
import * as chatApi from '@/api/chat'
import { useRoomStream, type StreamMessage } from '@/hooks/useRoomStream'

interface ChatContextValue {
  chats: Chat[]
  characters: Character[]
  characterPresets: CharacterPreset[]
  activeChat: Chat | null
  messages: Message[]
  feed: FeedItem[]
  isLoading: boolean
  isMessagesLoading: boolean
  selectChat: (chat: Chat | null) => void
  createChat: (data: { title: string; description?: string }) => Promise<Chat>
  addCharacterToChat: (chatId: string, presetId: string) => Promise<void>
  removeCharacterFromChat: (chatId: string, agentId: string) => Promise<void>
  sendMessage: (chatId: string, agentId: string, content: string) => Promise<void>
  sendEvent: (chatId: string, description: string, agentIds?: string[]) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  refreshChats: () => Promise<void>
  /** Обновить чаты в фоне без индикатора загрузки */
  refreshChatsSilent: () => Promise<void>
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
  const [activeChat, setActiveChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [feed, setFeed] = useState<FeedItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)

  const characterPresets = chatApi.getCharacterPresets()

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
    try {
      const [msgs, feedItems, agents] = await Promise.all([
        chatApi.fetchMessages(chatId),
        chatApi.fetchFeed(chatId),
        chatApi.fetchCharacters(chatId),
      ])
      setMessages(msgs)
      setFeed(feedItems.sort(sortFeed))
      setCharacters(agents)
    } catch (err) {
      console.error('Failed to load messages:', err)
      setMessages([])
      setFeed([])
      setCharacters([])
    } finally {
      setIsMessagesLoading(false)
    }
  }, [])

  useEffect(() => {
    loadChats()
  }, [loadChats])

  useEffect(() => {
    if (activeChat) {
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
      if (msg.type === 'event') {
        const p = msg.payload as { id: string; description: string; agentIds: string[]; timestamp: string }
        setFeed((prev) =>
          [
            ...prev,
            {
              type: 'event' as const,
              data: {
                id: p.id,
                chatId: activeChat.id,
                type: 'user_event' as const,
                description: p.description,
                agentIds: p.agentIds ?? [],
                timestamp: p.timestamp,
              },
            },
          ].sort(sortFeed)
        )
      }
      if (msg.type === 'message') {
        const p = msg.payload as { id: string; text: string; agentId?: string; timestamp: string }
        const data: Message = {
          id: p.id,
          chatId: activeChat.id,
          characterId: p.agentId ?? '',
          content: p.text,
          timestamp: p.timestamp,
          isRead: false,
        }
        setMessages((prev) => [...prev, data])
        setFeed((prev) => [...prev, { type: 'message', data }].sort(sortFeed))
      }
    },
    [activeChat]
  )

  useRoomStream({
    roomId: activeChat?.id ?? null,
    onMessage: handleStreamMessage,
    enabled: !!activeChat,
  })

  const selectChat = useCallback((chat: Chat | null) => {
    setActiveChat(chat)
  }, [])

  const createChat = useCallback(async (data: { title: string; description?: string }) => {
    const chat = await chatApi.createChat(data)
    const chatsData = await chatApi.fetchChats()
    setChats(chatsData)
    const updated = chatsData.find((c) => c.id === chat.id) ?? chat
    setActiveChat(updated)
    return updated
  }, [])

  const addCharacterToChat = useCallback(async (chatId: string, presetId: string) => {
    const updated = await chatApi.addCharacterToChat(chatId, presetId)
    if (updated) {
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)))
      if (activeChat?.id === chatId) {
        setActiveChat(updated)
        await loadMessages(chatId)
      }
    }
  }, [activeChat?.id, loadMessages])

  const removeCharacterFromChat = useCallback(async (chatId: string, agentId: string) => {
    const updated = await chatApi.removeCharacterFromChat(chatId, agentId)
    if (updated) {
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)))
      if (activeChat?.id === chatId) {
        setActiveChat(updated)
        await loadMessages(chatId)
      }
    }
  }, [activeChat?.id, loadMessages])

  const sendMessage = useCallback(async (chatId: string, agentId: string, content: string) => {
    await chatApi.sendMessage(chatId, agentId, content)
    await loadMessages(chatId)
  }, [loadMessages])

  const sendEvent = useCallback(async (chatId: string, description: string, agentIds: string[] = []) => {
    await chatApi.sendEvent(chatId, description, agentIds)
    await loadMessages(chatId)
  }, [loadMessages])

  const deleteChat = useCallback(async (chatId: string) => {
    await chatApi.deleteChat(chatId)
    const chatsData = await chatApi.fetchChats()
    setChats(chatsData)
    if (activeChat?.id === chatId) setActiveChat(null)
  }, [activeChat?.id])

  const value: ChatContextValue = {
    chats,
    characters,
    characterPresets,
    activeChat,
    messages,
    feed,
    isLoading,
    isMessagesLoading,
    selectChat,
    createChat,
    addCharacterToChat,
    removeCharacterFromChat,
    sendMessage,
    sendEvent,
    deleteChat,
    refreshChats: loadChats,
    refreshChatsSilent,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
