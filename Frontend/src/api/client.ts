/**
 * API-клиент для бэкенда
 * В dev: относительные URL (/api/...) — через Vite proxy, без CORS
 * В prod: VITE_API_URL или http://5.39.250.179:8000
 *
 * Все ручки кроме auth требуют Bearer-токен (skipAuth: true только для login/register).
 * При 401 вызывается onUnauthorized (logout и редирект на /login).
 */

const API_BASE = import.meta.env.DEV
  ? ''
  : (import.meta.env.VITE_API_URL ?? 'http://5.39.250.179:8000')

let tokenGetter: (() => string | null) | null = null
let onUnauthorized: (() => void) | null = null

export function setTokenGetter(fn: () => string | null) {
  tokenGetter = fn
}

export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

export function getToken(): string | null {
  return tokenGetter?.() ?? null
}

export function getApiBase(): string {
  return API_BASE.replace(/\/$/, '')
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly detail?: string | Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
    Object.setPrototypeOf(this, ApiError.prototype)
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, ...init } = options
  const url = path.startsWith('http') ? path : `${getApiBase()}${path.startsWith('/') ? '' : '/'}${path}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  }

  if (!skipAuth) {
    const token = getToken()
    if (!token) {
      throw new ApiError('Требуется авторизация', 401)
    }
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(url, {
    ...init,
    headers,
  })

  if (res.status === 401 && !skipAuth) {
    onUnauthorized?.()
    throw new ApiError('Сессия истекла. Войдите снова.', 401)
  }

  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = await res.json().catch(() => ({}))
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    } catch {
      detail = await res.text()
    }
    const message = detail || res.statusText || `HTTP ${res.status}`
    throw new ApiError(message, res.status, detail as string | Record<string, unknown>)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}
