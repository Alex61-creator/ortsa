import { type ReactNode, useEffect, useMemo } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, App as AntApp } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import { HelmetProvider } from 'react-helmet-async'
import { BrowserRouter } from 'react-router-dom'
import { queryClient } from '@/lib/queryClient'
import { getAntdTheme } from '@/lib/theme'
import { useEffectiveThemeMode } from '@/hooks/useEffectiveThemeMode'
import { TwaAuthBootstrap } from '@/components/TwaAuthBootstrap'

dayjs.locale('ru')

export function AppProviders({ children }: { children: ReactNode }) {
  const effectiveMode = useEffectiveThemeMode()
  const theme = useMemo(() => getAntdTheme(effectiveMode), [effectiveMode])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', effectiveMode)
  }, [effectiveMode])

  return (
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={ruRU} theme={theme}>
          <AntApp>
            <BrowserRouter>
              <TwaAuthBootstrap />
              {children}
            </BrowserRouter>
          </AntApp>
        </ConfigProvider>
      </QueryClientProvider>
    </HelmetProvider>
  )
}
