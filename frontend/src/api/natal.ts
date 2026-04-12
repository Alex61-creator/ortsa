import { api } from '@/api/client'
import type { NatalDataCreatePayload, NatalDataOut, NatalDataUpdatePayload } from '@/types/api'

export async function listNatalData(): Promise<NatalDataOut[]> {
  const { data } = await api.get<NatalDataOut[]>('/natal-data/')
  return data
}

export async function createNatalData(payload: NatalDataCreatePayload): Promise<NatalDataOut> {
  const { data } = await api.post<NatalDataOut>('/natal-data/', payload)
  return data
}

export async function updateNatalData(
  id: number,
  payload: NatalDataUpdatePayload
): Promise<NatalDataOut> {
  const { data } = await api.patch<NatalDataOut>(`/natal-data/${id}`, payload)
  return data
}

export async function deleteNatalData(id: number): Promise<void> {
  await api.delete(`/natal-data/${id}`)
}
