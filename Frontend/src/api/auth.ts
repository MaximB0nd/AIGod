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
