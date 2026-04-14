import { api } from '@/api/client'

export interface TariffHistoryRow {
  id: string
  tariff_id: number
  actor: string
  payload: Record<string, unknown>
  created_at: string
}

export async function fetchTariffHistory() {
  const { data } = await api.get<TariffHistoryRow[]>('/api/v1/admin/tariffs/history/list')
  return data
}
