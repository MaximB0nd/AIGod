/**
 * Ключи localStorage, используемые приложением
 */

export const STORAGE_KEYS = {
  AUTH: 'aigod_auth',
  SIDEBAR_WIDTH: 'chats-sidebar-width',
  RIGHT_PANEL_WIDTH: 'chats-right-panel-width',
} as const

const ALL_KEYS = Object.values(STORAGE_KEYS)

/**
 * Очищает все данные приложения из localStorage.
 * Вызывать при выходе и при первом заходе на страницу авторизации,
 * чтобы избежать конфликтов с токенами.
 */
export function clearAllAppStorage(): void {
  try {
    ALL_KEYS.forEach((key) => localStorage.removeItem(key))
  } catch {
    // ignore
  }
}
