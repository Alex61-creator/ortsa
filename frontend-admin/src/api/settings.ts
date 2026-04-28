import { api } from '@/api/client'
import type { AppSettingRow, LlmProviderConfig, LlmProvidersOut } from '@/types/admin'

export async function fetchSettings(): Promise<AppSettingRow[]> {
  const { data } = await api.get<AppSettingRow[]>('/api/v1/admin/settings/')
  return data
}

export async function updateSetting(key: string, value: string): Promise<AppSettingRow> {
  const { data } = await api.patch<AppSettingRow>(`/api/v1/admin/settings/${key}`, { value })
  return data
}

// ── LLM провайдеры ────────────────────────────────────────────────────────────

export async function fetchLlmProviders(): Promise<LlmProvidersOut> {
  const { data } = await api.get<LlmProvidersOut>('/api/v1/admin/settings/llm-providers')
  return data
}

export async function toggleLlmProvider(provider: string, enabled: boolean): Promise<LlmProviderConfig> {
  const { data } = await api.put<LlmProviderConfig>(
    `/api/v1/admin/settings/llm-providers/${provider}/toggle`,
    { enabled },
  )
  return data
}

export async function setLlmFallbackOrder(order: string[]): Promise<{ fallback_order: string[] }> {
  const { data } = await api.put<{ fallback_order: string[] }>(
    '/api/v1/admin/settings/llm-providers/order',
    { order },
  )
  return data
}
