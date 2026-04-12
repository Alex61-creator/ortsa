import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'dark' | 'light'

interface ThemeState {
  mode: ThemeMode
  setMode: (m: ThemeMode) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'dark',
      setMode: (mode) => set({ mode }),
    }),
    { name: 'astrogen_theme' }
  )
)
