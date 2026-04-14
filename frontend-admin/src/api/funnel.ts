import { api } from '@/api/client'
import type { FunnelSummary } from '@/types/admin'

export async function fetchFunnelSummary(period = 'current_month') {
  const { data } = await api.get<FunnelSummary>('/api/v1/admin/funnel/summary', { params: { period } })
  return data
}
