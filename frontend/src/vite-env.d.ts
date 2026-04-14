/// <reference types="vite/client" />

interface TelegramWebApp {
  colorScheme?: 'light' | 'dark'
  initData?: string
  platform?: string
  ready?: () => void
  expand?: () => void
  openLink?: (url: string) => void
}

interface TelegramNamespace {
  WebApp?: TelegramWebApp
}

declare global {
  interface Window {
    Telegram?: TelegramNamespace
  }
}

export {}

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_APP_ORIGIN?: string
  readonly VITE_GEOCODER_USER_AGENT?: string
  /** Полная ссылка t.me/... на Mini App (опционально для UI-кнопок). */
  readonly VITE_TELEGRAM_MINIAPP_URL?: string
}
