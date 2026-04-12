import { api, getApiBaseUrl } from '@/api/client'
import type { TwAuthResponse } from '@/types/api'

export async function authTwa(initData: string): Promise<TwAuthResponse> {
  const { data } = await api.post<TwAuthResponse>('/auth/twa', { initData })
  return data
}

export function getOAuthAuthorizeUrl(provider: 'google' | 'yandex' | 'apple'): string {
  const base = getApiBaseUrl().replace(/\/$/, '')
  return `${base}/auth/${provider}/authorize`
}
