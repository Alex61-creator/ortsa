import { api } from '@/api/client'
import type { AdminTaskRow } from '@/types/admin'

export async function fetchTasks() {
  const { data } = await api.get<AdminTaskRow[]>('/api/v1/admin/tasks/')
  return data
}
