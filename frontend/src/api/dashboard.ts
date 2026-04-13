import { api } from '@/api/client'
import type { OrderListItem } from '@/types/api'

export interface DashboardSubscriptionBrief {
  tariff_name: string
  tariff_code: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
}

export interface DashboardSummary {
  natal_count: number
  reports_ready_count: number
  subscription: DashboardSubscriptionBrief | null
  recent_orders: OrderListItem[]
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>('/users/me/dashboard-summary')
  return data
}
