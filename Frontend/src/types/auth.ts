/**
 * Типы для авторизации (по BACKEND_API_REQUIREMENTS.md)
 */

export interface AuthUser {
  id: string
  email: string
  username: string
}

export interface AuthResponse {
  id: string
  email: string
  username: string
  token: string
  /** Не возвращается в новом контракте AIgod */
  refreshToken?: string
}

export interface RegisterRequest {
  email: string
  password: string
  username: string
}

export interface LoginRequest {
  email: string
  password: string
}
