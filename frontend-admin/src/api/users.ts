import { api } from '@/api/client'
import type { AdminUserRow } from '@/types/admin'

export interface UsersListParams {
  page?: number
  page_size?: number
  q?: string
}

export async function fetchUsers(params: UsersListParams): Promise<AdminUserRow[]> {
  const { data } = await api.get<AdminUserRow[]>('/api/v1/admin/users', { params })
  return data
}

export async function deleteUser(userId: number): Promise<{ deleted: boolean; user_id: number }> {
  const { data } = await api.delete<{ deleted: boolean; user_id: number }>(
    `/api/v1/admin/users/${userId}`
  )
  return data
}
