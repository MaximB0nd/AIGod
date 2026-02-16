/**
 * API авторизации (моки, готов к замене на реальные запросы)
 * См. docs/BACKEND_API_REQUIREMENTS.md
 */

import type { AuthResponse, RegisterRequest, LoginRequest } from '@/types/auth'

const API_BASE = '/api' // для будущей интеграции

// --- Моки ---

function generateMockToken(): string {
  return `mock_jwt_${Date.now()}_${Math.random().toString(36).slice(2)}`
}

function mockAuthResponse(email: string, username: string): AuthResponse {
  return {
    id: `user-${Date.now()}`,
    email,
    username,
    token: generateMockToken(),
    refreshToken: generateMockToken(),
  }
}

// --- API функции ---

/**
 * POST /api/auth/register
 * Регистрация нового пользователя
 */
export async function register(data: RegisterRequest): Promise<AuthResponse> {
  // TODO: заменить на реальный запрос:
  // const res = await fetch(`${API_BASE}/auth/register`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(data),
  // })
  // if (!res.ok) throw new Error('Registration failed')
  // return res.json()

  // Имитация задержки сети
  await new Promise((r) => setTimeout(r, 400))

  if (!data.email?.trim() || !data.password?.trim() || !data.username?.trim()) {
    throw new Error('Заполните все поля')
  }

  return Promise.resolve(mockAuthResponse(data.email, data.username))
}

/**
 * POST /api/auth/login
 * Вход в аккаунт
 */
export async function login(data: LoginRequest): Promise<AuthResponse> {
  // TODO: заменить на реальный запрос:
  // const res = await fetch(`${API_BASE}/auth/login`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(data),
  // })
  // if (!res.ok) throw new Error('Login failed')
  // return res.json()

  await new Promise((r) => setTimeout(r, 400))

  if (!data.email?.trim() || !data.password?.trim()) {
    throw new Error('Введите email и пароль')
  }

  const username = data.email.split('@')[0]
  return Promise.resolve(mockAuthResponse(data.email, username))
}
