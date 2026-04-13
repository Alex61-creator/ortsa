import { api } from '@/api/client'
import type { DashboardSummary } from '@/types/admin'

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>('/api/v1/admin/dashboard/summary')
  return data
}
