import { api } from '@/api/client'

export interface UserNoteRow {
  id: string
  text: string
  created_at: string
}

export async function listUserNotes(userId: number) {
  const { data } = await api.get<UserNoteRow[]>(`/admin/support/users/${userId}/notes`)
  return data
}

export async function addUserNote(userId: number, text: string) {
  const { data } = await api.post<UserNoteRow>(`/admin/support/users/${userId}/notes`, { text })
  return data
}

export async function patchUserEmail(userId: number, email: string) {
  const { data } = await api.patch(`/admin/support/users/${userId}/email`, { email })
  return data
}

export async function blockUser(userId: number) {
  const { data } = await api.post(`/admin/support/users/${userId}/block`)
  return data
}

export async function unblockUser(userId: number) {
  const { data } = await api.post(`/admin/support/users/${userId}/unblock`)
  return data
}
