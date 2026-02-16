/**
 * Контекст чатов нейросетей
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
import * as chatApi from '@/api/chat'

interface ChatContextValue {
  chats: Chat[]
  characters: Character[]
  activeChat: Chat | null
  messages: Message[]
  feed: FeedItem[]
  isLoading: boolean
  selectChat: (chat: Chat | null) => void
  createChat: (data: { title: string; characterIds: string[] }) => Promise<Chat>
  addCharacterToChat: (chatId: string, characterId: string) => Promise<void>
  removeCharacterFromChat: (chatId: string, characterId: string) => Promise<void>
  sendMessage: (chatId: string, characterId: string, content: string) => Promise<void>
  sendEvent: (chatId: string, description: string, agentIds?: string[]) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  refreshChats: () => Promise<void>
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

  const loadChats = useCallback(async () => {
    try {
      const [chatsData, charsData] = await Promise.all([
        chatApi.fetchChats(),
        chatApi.fetchCharacters(),
      ])
      setChats(chatsData)
      setCharacters(charsData)
    } catch (err) {
      console.error('Failed to load chats:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadMessages = useCallback(async (chatId: string) => {
    try {
      const [msgs, feedItems] = await Promise.all([
        chatApi.fetchMessages(chatId),
        chatApi.fetchFeed(chatId),
      ])
      setMessages(msgs)
      setFeed(feedItems)
    } catch (err) {
      console.error('Failed to load messages:', err)
      setMessages([])
      setFeed([])
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
    }
  }, [activeChat?.id, loadMessages])

  const selectChat = useCallback((chat: Chat | null) => {
    setActiveChat(chat)
  }, [])

  const createChat = useCallback(async (data: { title: string; characterIds: string[] }) => {
    const chat = await chatApi.createChat(data)
    setChats((prev) => [...prev, chat])
    setActiveChat(chat)
    return chat
  }, [])

  const addCharacterToChat = useCallback(async (chatId: string, characterId: string) => {
    const updated = await chatApi.addCharacterToChat(chatId, characterId)
    if (updated) {
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)))
      if (activeChat?.id === chatId) setActiveChat(updated)
    }
  }, [activeChat?.id])

  const removeCharacterFromChat = useCallback(async (chatId: string, characterId: string) => {
    const updated = await chatApi.removeCharacterFromChat(chatId, characterId)
    if (updated) {
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)))
      if (activeChat?.id === chatId) setActiveChat(updated)
    }
  }, [activeChat?.id])

  const sendMessage = useCallback(async (chatId: string, characterId: string, content: string) => {
    const msg = await chatApi.sendMessage(chatId, characterId, content)
    setMessages((prev) => [...prev, msg])
    setFeed((prev) => [...prev, { type: 'message', data: msg }].sort(sortFeed))
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? { ...c, lastMessage: { content, timestamp: msg.timestamp, characterId } }
          : c
      )
    )
  }, [])

  const sendEvent = useCallback(async (chatId: string, description: string, agentIds: string[] = []) => {
    const evt = await chatApi.sendEvent(chatId, description, agentIds)
    setFeed((prev) => [...prev, { type: 'event', data: evt }].sort(sortFeed))
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? { ...c, lastMessage: { content: description, timestamp: evt.timestamp, characterId: '_narrator' } }
          : c
      )
    )
  }, [])

  const deleteChat = useCallback(async (chatId: string) => {
    await chatApi.deleteChat(chatId)
    setChats((prev) => prev.filter((c) => c.id !== chatId))
    if (activeChat?.id === chatId) setActiveChat(null)
  }, [activeChat?.id])

  const value: ChatContextValue = {
    chats,
    characters,
    activeChat,
    messages,
    feed,
    isLoading,
    selectChat,
    createChat,
    addCharacterToChat,
    removeCharacterFromChat,
    sendMessage,
    sendEvent,
    deleteChat,
    refreshChats: loadChats,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
