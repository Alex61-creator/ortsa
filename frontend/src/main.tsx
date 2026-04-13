import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/lib/i18n'
import '@/styles/global.css'
import { AppProviders } from '@/components/AppProviders'
import { AppRoutes } from '@/routes/AppRoutes'
import { useAuthStore } from '@/stores/authStore'

/** Синхронно до гидрации persist: JWT с лендинга в sessionStorage → в store (см. также onRehydrateStorage в authStore). */
function migrateLandingJwtSync(): void {
  try {
    const raw = localStorage.getItem('astrogen_auth_token')
    if (raw) {
      const p = JSON.parse(raw) as { state?: { token?: string | null } }
      if (p?.state?.token) return
    }
    const jwt = sessionStorage.getItem('astrogen_jwt')
    if (jwt) {
      useAuthStore.getState().setToken(jwt)
      sessionStorage.removeItem('astrogen_jwt')
    }
  } catch {
    /* ignore */
  }
}
migrateLandingJwtSync()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  </StrictMode>
)
