import { api } from '@/api/client'
import type { TariffPublic } from '@/types/api'

export async function listTariffs(): Promise<TariffPublic[]> {
  const { data } = await api.get<TariffPublic[]>('/tariffs/')
  return data
}
