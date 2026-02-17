/**
 * Контекст авторизации
 * Хранит токены и данные пользователя в localStorage
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { AuthUser, AuthResponse, RegisterRequest, LoginRequest } from '@/types/auth'
import * as authApi from '@/api/auth'
import { setTokenGetter, setUnauthorizedHandler } from '@/api/client'
import { clearAllAppStorage, STORAGE_KEYS } from '@/utils/storage'

const STORAGE_KEY = STORAGE_KEYS.AUTH

interface StoredAuth {
  user: AuthUser
  token: string
  refreshToken: string
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function loadStoredAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as StoredAuth
    if (!data?.user?.id || !data?.token) return null
    return data
  } catch {
    return null
  }
}

function saveAuth(data: AuthResponse): void {
  const stored: StoredAuth = {
    user: { id: data.id, email: data.email, username: data.username },
    token: data.token,
    refreshToken: data.refreshToken,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stored))
}

function clearAuth(): void {
  clearAllAppStorage()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = loadStoredAuth()
    if (stored) {
      setUser(stored.user)
      setToken(stored.token)
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    setTokenGetter(() => token)
  }, [token])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearAuth()
      setUser(null)
      setToken(null)
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const login = useCallback(async (data: LoginRequest) => {
    const res = await authApi.login(data)
    saveAuth(res)
    setUser({ id: res.id, email: res.email, username: res.username })
    setToken(res.token)
  }, [])

  const register = useCallback(async (data: RegisterRequest) => {
    const res = await authApi.register(data)
    saveAuth(res)
    setUser({ id: res.id, email: res.email, username: res.username })
    setToken(res.token)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setUser(null)
    setToken(null)
  }, [])

  const value: AuthContextValue = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    register,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
