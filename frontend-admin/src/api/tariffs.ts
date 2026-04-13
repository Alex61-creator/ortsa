import { api } from '@/api/client'
import type { TariffPatch, TariffRow } from '@/types/admin'

export async function fetchTariffs(): Promise<TariffRow[]> {
  const { data } = await api.get<TariffRow[]>('/api/v1/admin/tariffs/')
  return data
}

export async function patchTariff(tariffId: number, body: TariffPatch): Promise<TariffRow> {
  const { data } = await api.patch<TariffRow>(`/api/v1/admin/tariffs/${tariffId}`, body)
  return data
}
