/**
 * Онбординг для новых пользователей после регистрации
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './OnboardingPage.module.css'

const STEPS = [
  {
    icon: '✨',
    title: 'Добро пожаловать!',
    description: 'Виртуальный мир — это симулятор живых существ. Здесь персонажи-нейросети общаются, развиваются и создают свою историю.',
  },
  {
    icon: '💬',
    title: 'Создавайте чаты',
    description: 'Добавляйте персонажей в комнаты и наблюдайте, как они общаются друг с другом. Каждый диалог уникален и непредсказуем.',
  },
  {
    icon: '🧠',
    title: 'Живая память',
    description: 'Персонажи помнят контекст и развиваются со временем. Их отношения, воспоминания и характер формируются в каждом сообщении.',
  },
  {
    icon: '🚀',
    title: 'Всё готово!',
    description: 'Нажмите «Начать» и погрузитесь в виртуальный мир. Создайте первый чат и добавьте персонажей.',
  },
]

export function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [isExiting, setIsExiting] = useState(false)

  const goToMainFlow = useCallback(() => {
    setIsExiting(true)
    setTimeout(() => navigate('/', { replace: true, state: { fromRegistration: false } }), 400)
  }, [navigate])

  const handleNext = useCallback(() => {
    if (step < STEPS.length - 1) {
      setStep((s) => s + 1)
    } else {
      goToMainFlow()
    }
  }, [step, goToMainFlow])

  const handleSkip = useCallback(() => {
    goToMainFlow()
  }, [goToMainFlow])

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  return (
    <div className={`${styles.wrapper} ${isExiting ? styles.exiting : ''}`}>
      <div className={styles.bg}>
        <div className={styles.gradient} />
        <div className={styles.grid} />
      </div>

      <div className={styles.content}>
        <button type="button" className={styles.skip} onClick={handleSkip}>
          Пропустить
        </button>

        <div className={styles.card}>
          <div className={styles.iconWrap}>{current.icon}</div>
          <h1 className={styles.title}>{current.title}</h1>
          <p className={styles.description}>{current.description}</p>

          <div className={styles.dots}>
            {STEPS.map((_, i) => (
              <button
                key={i}
                type="button"
                className={`${styles.dot} ${i === step ? styles.dotActive : ''}`}
                onClick={() => setStep(i)}
                aria-label={`Шаг ${i + 1}`}
              />
            ))}
          </div>

          <button
            type="button"
            className={styles.cta}
            onClick={handleNext}
          >
            {isLast ? 'Начать' : 'Далее'}
          </button>
        </div>
      </div>
    </div>
  )
}
