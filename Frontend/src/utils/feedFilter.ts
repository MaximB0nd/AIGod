/**
 * Сообщения суммаризатора и системных агентов не отображаются в чате.
 * Их никто не должен видеть.
 */

/** Проверяет, является ли сообщение скрытым (суммаризатор или системный агент) */
export function isHiddenSystemMessage(sender: string | undefined): boolean {
  if (!sender || typeof sender !== 'string') return false
  const s = sender.trim()
  if (!s) return false
  // system / Система
  if (s === 'system' || s === 'Система') return true
  // Суммаризатор и варианты отображения
  if (
    s === 'Суммаризатор' ||
    s.includes('Суммаризатор') ||
    s.includes('Сводка Суммаризатор') ||
    s.startsWith('📊')
  ) {
    return true
  }
  return false
}

/** Фильтрует feed: убирает сообщения от суммаризатора и системных агентов */
export function filterVisibleFeed<T extends { type: string; data: { sender?: string } }>(
  items: T[]
): T[] {
  return items.filter((item) => {
    if (item.type !== 'message') return true
    const sender = (item.data as { sender?: string }).sender
    return !isHiddenSystemMessage(sender)
  })
}
