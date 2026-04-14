import { api } from '@/api/client'
import type { AdminPaymentRow } from '@/types/admin'

export async function fetchPayments(params: { page?: number; page_size?: number; status?: string; q?: string } = {}) {
  const { data } = await api.get<AdminPaymentRow[]>('/api/v1/admin/payments/', { params })
  return data
}
