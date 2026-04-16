import { api } from '@/api/client'
import type { AdminLogRow } from '@/types/admin'

export async function fetchAdminLogs(params: { actor?: string; action?: string; entity?: string; limit?: number } = {}) {
  const { data } = await api.get<AdminLogRow[]>('/api/v1/admin/logs/', { params })
  return data
}
