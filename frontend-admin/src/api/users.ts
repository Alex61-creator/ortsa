import { api } from '@/api/client'
import type { AdminSynastryReportRow, AdminUserRow, SynastryOverrideRow } from '@/types/admin'

export interface UsersListParams {
  page?: number
  page_size?: number
  q?: string
}

export async function fetchUsers(params: UsersListParams): Promise<AdminUserRow[]> {
  const { data } = await api.get<AdminUserRow[]>('/api/v1/admin/users/', { params })
  return data
}

export async function deleteUser(userId: number): Promise<{ deleted: boolean; user_id: number }> {
  const { data } = await api.delete<{ deleted: boolean; user_id: number }>(
    `/api/v1/admin/users/${userId}`
  )
  return data
}

// ── Synastry override ─────────────────────────────────────────────────────────

export async function fetchSynastryOverride(userId: number): Promise<SynastryOverrideRow> {
  const { data } = await api.get<SynastryOverrideRow>(
    `/api/v1/admin/users/${userId}/synastry/override`
  )
  return data
}

export interface SynastryOverridePatch {
  synastry_enabled?: boolean
  free_synastries_granted?: number
  admin_note?: string | null
}

export async function patchSynastryOverride(
  userId: number,
  payload: SynastryOverridePatch
): Promise<SynastryOverrideRow> {
  const { data } = await api.patch<SynastryOverrideRow>(
    `/api/v1/admin/users/${userId}/synastry/override`,
    payload
  )
  return data
}

export async function fetchUserSynastryReports(
  userId: number
): Promise<AdminSynastryReportRow[]> {
  const { data } = await api.get<AdminSynastryReportRow[]>(
    `/api/v1/admin/users/${userId}/synastry/reports`
  )
  return data
}

export async function deleteUserSynastryReport(
  userId: number,
  reportId: number
): Promise<void> {
  await api.delete(`/api/v1/admin/users/${userId}/synastry/reports/${reportId}`)
}
