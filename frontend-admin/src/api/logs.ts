import { api } from '@/api/client'
import type { AdminLogRow } from '@/types/admin'

export async function fetchAdminLogs() {
  const { data } = await api.get<AdminLogRow[]>('/api/v1/admin/logs/')
  return data
}
