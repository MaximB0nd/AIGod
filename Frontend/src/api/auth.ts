/**
 * API авторизации
 * @see docs/BACKEND_API_REQUIREMENTS.md
 */

import { apiFetch } from './client'
import type { AuthResponse, RegisterRequest, LoginRequest } from '@/types/auth'

/**
 * POST /api/auth/register
 */
export async function register(data: RegisterRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
    skipAuth: true,
  })
}

/**
 * POST /api/auth/login
 */
export async function login(data: LoginRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
    skipAuth: true,
  })
}

/**
 * GET /api/auth/me — текущий пользователь (Bearer token)
 * token и refreshToken в ответе пустые — клиент хранит токен из login
 */
export async function getMe(): Promise<AuthUser> {
  const res = await apiFetch<{ id: string; email: string; username: string }>(
    '/api/auth/me'
  )
  return { id: res.id, email: res.email, username: res.username }
}
