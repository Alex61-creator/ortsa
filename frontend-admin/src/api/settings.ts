import { api } from '@/api/client'
import type { AppSettingRow } from '@/types/admin'

export async function fetchSettings(): Promise<AppSettingRow[]> {
  const { data } = await api.get<AppSettingRow[]>('/api/v1/admin/settings/')
  return data
}

export async function updateSetting(key: string, value: string): Promise<AppSettingRow> {
  const { data } = await api.patch<AppSettingRow>(`/api/v1/admin/settings/${key}`, { value })
  return data
}
