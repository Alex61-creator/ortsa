import { useMemo } from 'react'
import { useThemeStore } from '@/stores/themeStore'
import { useTwaEnvironment } from '@/hooks/useTwaEnvironment'

/** Режим темы: в TWA — из Telegram, в браузере — из Zustand. */
export function useEffectiveThemeMode(): 'light' | 'dark' {
  const mode = useThemeStore((s) => s.mode)
  const { isTwa, colorScheme } = useTwaEnvironment()

  return useMemo(() => {
    if (isTwa) return colorScheme === 'light' ? 'light' : 'dark'
    return mode
  }, [isTwa, colorScheme, mode])
}
