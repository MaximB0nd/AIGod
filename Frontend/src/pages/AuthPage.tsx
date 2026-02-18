/**
 * Страница авторизации и регистрации
 * При монтировании очищает все данные приложения (токены, настройки),
 * чтобы избежать конфликтов при первом заходе или после выхода.
 */

import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { clearAllAppStorage } from '@/utils/storage'
import styles from './AuthPage.module.css'

type Tab = 'login' | 'register'

export function AuthPage() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('login')

  useEffect(() => {
    clearAllAppStorage()
  }, [])
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regUsername, setRegUsername] = useState('')

  const handleLogin = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      setIsSubmitting(true)
      try {
        await login({ email: loginEmail, password: loginPassword })
        navigate('/', { replace: true })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка входа')
      } finally {
        setIsSubmitting(false)
      }
    },
    [login, loginEmail, loginPassword, navigate]
  )

  const handleRegister = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      setIsSubmitting(true)
      try {
        await register({
          email: regEmail,
          password: regPassword,
          ...(regUsername.trim() && { username: regUsername.trim() }),
        })
        navigate('/', { replace: true, state: { fromRegistration: true } })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ошибка регистрации')
      } finally {
        setIsSubmitting(false)
      }
    },
    [register, regEmail, regPassword, regUsername, navigate]
  )

  const switchTab = useCallback((t: Tab) => {
    setTab(t)
    setError(null)
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <img src="/logo.png" alt="AmICreator" className={styles.logo} />
          <h1 className={styles.title}>Симулятор создателя</h1>
        </div>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${tab === 'login' ? styles.tabActive : ''}`}
            onClick={() => switchTab('login')}
          >
            Вход
          </button>
          <button
            type="button"
            className={`${styles.tab} ${tab === 'register' ? styles.tabActive : ''}`}
            onClick={() => switchTab('register')}
          >
            Регистрация
          </button>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        {tab === 'login' ? (
          <form onSubmit={handleLogin} className={styles.form}>
            <label className={styles.label}>
              Email
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="user@example.com"
                className={styles.input}
                required
                autoComplete="email"
              />
            </label>
            <label className={styles.label}>
              Пароль
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className={styles.input}
                required
                autoComplete="current-password"
              />
            </label>
            <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
              {isSubmitting ? 'Вход...' : 'Войти'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className={styles.form}>
            <label className={styles.label}>
              Email
              <input
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="user@example.com"
                className={styles.input}
                required
                autoComplete="email"
              />
            </label>
            <label className={styles.label}>
              Имя пользователя (необязательно)
              <input
                type="text"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="По умолчанию — часть до @ из email"
                className={styles.input}
                autoComplete="username"
              />
            </label>
            <label className={styles.label}>
              Пароль
              <input
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="••••••••"
                className={styles.input}
                required
                autoComplete="new-password"
              />
            </label>
            <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
              {isSubmitting ? 'Регистрация...' : 'Зарегистрироваться'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
