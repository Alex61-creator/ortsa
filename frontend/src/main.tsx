import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/lib/i18n'
import '@/styles/global.css'
import { AppProviders } from '@/components/AppProviders'
import { AppRoutes } from '@/routes/AppRoutes'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  </StrictMode>
)
