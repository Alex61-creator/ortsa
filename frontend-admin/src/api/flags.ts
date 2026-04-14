import { api } from '@/api/client'
import type { FeatureFlagRow } from '@/types/admin'

export async function fetchFlags() {
  const { data } = await api.get<FeatureFlagRow[]>('/api/v1/admin/flags/')
  return data
}

export async function patchFlag(flagKey: string, enabled: boolean) {
  const { data } = await api.patch<FeatureFlagRow>(`/api/v1/admin/flags/${flagKey}`, { enabled })
  return data
}
