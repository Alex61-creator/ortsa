import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const STORAGE_KEY = 'astrogen_admin_auth_token'

interface AuthState {
  token: string | null
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
      logout: () => set({ token: null }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (s) => ({ token: s.token }),
    }
  )
)
