import { api } from '@/api/client'
import type { UserMe } from '@/types/api'

export async function fetchMe(): Promise<UserMe> {
  const { data } = await api.get<UserMe>('/users/me')
  return data
}

export async function patchMeConsent(accept: boolean): Promise<UserMe> {
  const { data } = await api.patch<UserMe>('/users/me', { accept_privacy_policy: accept })
  return data
}

export async function exportUserData(): Promise<Blob> {
  const { data } = await api.get<Blob>('/users/me/export', { responseType: 'blob' })
  return data
}

export async function deleteAccount(): Promise<void> {
  await api.delete('/users/me')
}
