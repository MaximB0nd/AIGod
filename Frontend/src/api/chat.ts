/**
 * API чатов — маппинг Room/Agent на Chat/Character
 * Использует rooms, agents, events, feed, messages
 */

import type { Chat, Message, Character, Event, FeedItem } from '@/types/chat'
import * as roomsApi from './rooms'
import * as agentsApi from './agents'
import * as eventsApi from './events'
import * as feedApi from './feed'
import * as messagesApi from './messages'
import { CHARACTER_PRESETS } from '@/constants/characterPresets'

function roomToChat(room: Awaited<ReturnType<typeof roomsApi.fetchRoom>>, agentIds: string[]): Chat | null {
  if (!room) return null
  return {
    id: room.id,
    title: room.name,
    characterIds: agentIds,
    createdAt: room.createdAt,
  }
}

function agentToCharacter(a: { id: string; name: string; avatar?: string; mood?: { mood: string; level: number } }): Character {
  return {
    id: a.id,
    name: a.name,
    avatar: a.avatar,
    description: a.mood?.mood,
  }
}

export function getCharacterPresets() {
  return CHARACTER_PRESETS
}

export async function fetchChats(): Promise<Chat[]> {
  const roomList = await roomsApi.fetchRooms()
  const agentsByRoom = await Promise.all(
    roomList.map((room) => agentsApi.fetchAgents(room.id))
  )
  return roomList
    .map((room, i) => roomToChat(room, agentsByRoom[i].map((a) => a.id)))
    .filter((c): c is Chat => c != null)
}

export async function fetchChat(chatId: string): Promise<Chat | null> {
  const room = await roomsApi.fetchRoom(chatId)
  if (!room) return null
  const agents = await agentsApi.fetchAgents(chatId)
  return roomToChat(room, agents.map((a) => a.id))
}

export async function fetchMessages(chatId: string): Promise<Message[]> {
  const items = await feedApi.fetchFeed(chatId)
  const agents = await agentsApi.fetchAgents(chatId)
  const agentMap = new Map(agents.map((a) => [a.id, a]))

  return items
    .filter((i): i is typeof i & { type: 'message' } => i.type === 'message')
    .map((i) => ({
      id: i.id,
      chatId,
      characterId: i.agentId ?? '',
      content: i.text,
      timestamp: i.timestamp,
      isRead: true,
    }))
}

export async function fetchFeed(chatId: string): Promise<FeedItem[]> {
  const items = await feedApi.fetchFeed(chatId, 20)
  return items.map((i) => {
    if (i.type === 'message') {
      return {
        type: 'message' as const,
        data: {
          id: i.id,
          chatId,
          characterId: i.agentId ?? '',
          content: i.text ?? '',
          timestamp: i.timestamp,
          isRead: true,
          sender: (i as { sender?: 'user' | 'agent' | 'system' }).sender ?? 'agent',
        },
      }
    }
    return {
      type: 'event' as const,
      data: {
        id: i.id,
        chatId,
        type: ((i as { eventType?: string }).eventType ?? 'user_event') as string,
        description: (i as { description?: string }).description ?? '',
        agentIds: (i as { agentIds?: string[] }).agentIds ?? [],
        timestamp: i.timestamp,
      },
    }
  })
}

export async function sendEvent(
  chatId: string,
  description: string,
  agentIds: string[] = []
): Promise<Event> {
  if (agentIds.length === 0) {
    const evt = await eventsApi.broadcastEvent(chatId, { description })
    return {
      id: evt.id,
      chatId,
      type: 'user_event',
      description: evt.description,
      agentIds: evt.agentIds,
      timestamp: evt.timestamp,
    }
  }
  const evt = await eventsApi.createEvent(chatId, {
    description,
    type: 'user_event',
    agentIds,
  })
  return {
    id: evt.id,
    chatId,
    type: 'user_event',
    description: evt.description,
    agentIds: evt.agentIds,
    timestamp: evt.timestamp,
  }
}

export async function fetchCharacters(roomId: string): Promise<Character[]> {
  const agents = await agentsApi.fetchAgents(roomId)
  return agents.map(agentToCharacter)
}

/**
 * Загрузить сообщения, ленту и персонажей одним запросом (2 API-вызова вместо 4).
 * Используется в loadMessages для устранения дублирования fetchFeed и fetchAgents.
 */
export async function fetchMessagesFeedAndCharacters(chatId: string): Promise<{
  messages: Message[]
  feed: FeedItem[]
  characters: Character[]
}> {
  const [items, agents] = await Promise.all([
    feedApi.fetchFeed(chatId, 20),
    agentsApi.fetchAgents(chatId),
  ])
  const feed: FeedItem[] = items.map((i) => {
    if (i.type === 'message') {
      return {
        type: 'message' as const,
        data: {
          id: i.id,
          chatId,
          characterId: i.agentId ?? '',
          content: i.text,
          timestamp: i.timestamp,
          isRead: true,
          sender: (i as { sender?: 'user' | 'agent' | 'system' }).sender ?? 'agent',
        },
      }
    }
    return {
      type: 'event' as const,
      data: {
        id: i.id,
        chatId,
        type: ((i as { eventType?: string }).eventType ?? 'user_event') as string,
        description: (i as { description?: string }).description ?? '',
        agentIds: (i as { agentIds?: string[] }).agentIds ?? [],
        timestamp: i.timestamp,
      },
    }
  })
  const messages: Message[] = items
    .filter((i): i is typeof i & { type: 'message' } => i.type === 'message')
    .map((i) => ({
      id: i.id,
      chatId,
      characterId: i.agentId ?? '',
      content: i.text,
      timestamp: i.timestamp,
      isRead: true,
    }))
  return {
    messages,
    feed,
    characters: agents.map(agentToCharacter),
  }
}

export async function createChat(data: {
  title: string
  description?: string
}): Promise<Chat> {
  const room = await roomsApi.createRoom({
    name: data.title,
    // description опционально по API — не передаём при пустом значении
    ...(data.description != null && data.description.trim() !== '' && { description: data.description.trim() }),
  })

  return {
    id: room.id,
    title: room.name,
    characterIds: [],
    createdAt: room.createdAt,
  }
}

export async function addCharacterToChat(
  chatId: string,
  presetId: string
): Promise<void> {
  const preset = CHARACTER_PRESETS.find((p) => p.id === presetId)
  if (!preset) return

  await agentsApi.createAgent(chatId, {
    name: preset.name,
    character: preset.character,
  })
}

/**
 * Создать агента в комнате (POST /api/rooms/{roomId}/agents)
 * @see docs/BACKEND_API_REQUIREMENTS.md § 3.3
 */
export async function createAgentInChat(
  chatId: string,
  data: { name: string; character: string; avatar?: string }
): Promise<void> {
  await agentsApi.createAgent(chatId, data)
}

export async function removeCharacterFromChat(
  chatId: string,
  agentId: string
): Promise<void> {
  await agentsApi.deleteAgent(chatId, agentId)
}

export async function sendMessage(
  chatId: string,
  agentId: string,
  content: string
): Promise<Message> {
  const res = await messagesApi.sendMessage(chatId, agentId, {
    text: content,
    sender: 'user',
  })
  return {
    id: res.id,
    chatId,
    characterId: agentId ?? '',
    content: res.text,
    timestamp: res.timestamp,
    isRead: false,
  }
}

/**
 * Отправить сообщение в общий чат комнаты (всем агентам)
 * POST /api/rooms/{roomId}/messages
 */
export async function sendMessageToRoom(
  chatId: string,
  content: string
): Promise<Message> {
  const res = await messagesApi.sendMessageToRoom(chatId, {
    text: content,
    sender: 'user',
  })
  return {
    id: res.id,
    chatId,
    characterId: '',
    content: res.text,
    timestamp: res.timestamp,
    isRead: false,
  }
}

/**
 * Загрузить более старые сообщения (для ленивой загрузки при скролле вверх)
 * GET /api/rooms/{roomId}/messages?after_id=X
 */
export async function fetchOlderMessages(
  chatId: string,
  afterId: string,
  limit = 20
): Promise<{ items: FeedItem[]; hasMore: boolean }> {
  const numId = parseInt(afterId, 10)
  if (Number.isNaN(numId)) return { items: [], hasMore: false }

  const res = await messagesApi.fetchMessages(chatId, {
    after_id: numId,
    limit,
  })

  const items: FeedItem[] = (res.messages ?? []).map((m) => ({
    type: 'message' as const,
    data: {
      id: m.id,
      chatId,
      characterId: m.agentId ?? '',
      content: m.text,
      timestamp: m.timestamp,
      isRead: true,
      sender: m.sender ?? 'agent',
    },
  }))

  return { items, hasMore: res.hasMore ?? false }
}

export async function deleteChat(chatId: string): Promise<void> {
  await roomsApi.deleteRoom(chatId)
}
