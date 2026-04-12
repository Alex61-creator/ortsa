import { useEffect, useMemo } from 'react'

export interface TwaEnvironment {
  isTwa: boolean
  initData: string
  colorScheme: 'light' | 'dark'
}

/**
 * Определяет запуск внутри Telegram Mini App и подготавливает WebApp.
 */
export function useTwaEnvironment(): TwaEnvironment {
  useEffect(() => {
    if (typeof window === 'undefined') return
    const tg = window.Telegram?.WebApp
    const isRealTwa = Boolean(tg && (tg.initData || tg.platform !== 'unknown'))
    if (isRealTwa) {
      tg?.ready?.()
      tg?.expand?.()
    }
  }, [])

  return useMemo(() => {
    if (typeof window === 'undefined') {
      return { isTwa: false, initData: '', colorScheme: 'dark' as const }
    }
    const tg = window.Telegram?.WebApp
    const initData = tg?.initData ?? ''
    const isTwa = Boolean(tg && (initData || tg.platform !== 'unknown'))
    const cs = tg?.colorScheme === 'light' ? 'light' : 'dark'
    return { isTwa, initData, colorScheme: cs }
  }, [])
}
