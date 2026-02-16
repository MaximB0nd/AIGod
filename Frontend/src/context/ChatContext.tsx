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
import type { Chat, Message, Character } from '@/types/chat'
import * as chatApi from '@/api/chat'

interface ChatContextValue {
  chats: Chat[]
  characters: Character[]
  activeChat: Chat | null
  messages: Message[]
  isLoading: boolean
  selectChat: (chat: Chat | null) => void
  createChat: (data: { title: string; characterIds: string[] }) => Promise<Chat>
  addCharacterToChat: (chatId: string, characterId: string) => Promise<void>
  removeCharacterFromChat: (chatId: string, characterId: string) => Promise<void>
  sendMessage: (chatId: string, characterId: string, content: string) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
  refreshChats: () => Promise<void>
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([])
  const [characters, setCharacters] = useState<Character[]>([])
  const [activeChat, setActiveChat] = useState<Chat | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
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
      const msgs = await chatApi.fetchMessages(chatId)
      setMessages(msgs)
    } catch (err) {
      console.error('Failed to load messages:', err)
      setMessages([])
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
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? { ...c, lastMessage: { content, timestamp: msg.timestamp, characterId } }
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
    isLoading,
    selectChat,
    createChat,
    addCharacterToChat,
    removeCharacterFromChat,
    sendMessage,
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
