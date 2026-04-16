import { api } from '@/api/client'
import type { AdminTaskRow } from '@/types/admin'

export async function fetchTasks(params: { status?: string } = {}) {
  const { data } = await api.get<AdminTaskRow[]>('/api/v1/admin/tasks/', { params })
  return data
}
