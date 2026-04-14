import { api } from '@/api/client'
import type { PromoRow } from '@/types/admin'

export async function fetchPromos() {
  const { data } = await api.get<PromoRow[]>('/api/v1/admin/promos/')
  return data
}

export async function createPromo(payload: {
  code: string
  discount_percent: number
  max_uses: number
  active_until?: string | null
}) {
  const { data } = await api.post<PromoRow>('/api/v1/admin/promos/', payload)
  return data
}

export async function patchPromo(promoId: string, payload: Partial<Pick<PromoRow, 'is_active' | 'max_uses' | 'discount_percent'>>) {
  const { data } = await api.patch<PromoRow>(`/api/v1/admin/promos/${promoId}`, payload)
  return data
}
