import { api } from '@/api/client'
import type {
  FunnelSummary,
  MarketingSpendCreate,
  MarketingSpendRow,
  MetricsCohortsOut,
  MetricsEconomicsOut,
  MetricsOverviewOut,
} from '@/types/admin'

export async function fetchMetricsOverview(params: { period?: string } = {}) {
  const { data } = await api.get<MetricsOverviewOut>('/api/v1/admin/metrics/overview', { params })
  return data
}

export async function fetchMetricsFunnel(params: { period?: string } = {}) {
  const { data } = await api.get<FunnelSummary>('/api/v1/admin/metrics/funnel', { params })
  return data
}

export async function fetchMetricsCohorts(params: { period?: string } = {}) {
  const { data } = await api.get<MetricsCohortsOut>('/api/v1/admin/metrics/cohorts', { params })
  return data
}

export async function fetchMetricsEconomics(params: { period?: string } = {}) {
  const { data } = await api.get<MetricsEconomicsOut>('/api/v1/admin/metrics/economics', { params })
  return data
}

export async function fetchMarketingSpend() {
  const { data } = await api.get<MarketingSpendRow[]>('/api/v1/admin/metrics/spend')
  return data
}

export async function createMarketingSpend(payload: MarketingSpendCreate) {
  const { data } = await api.post<MarketingSpendRow>('/api/v1/admin/metrics/spend', payload)
  return data
}
