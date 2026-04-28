import { api } from '@/api/client'
import type {
  CampaignPerformanceOut,
  FunnelSummary,
  LlmMarginOut,
  LlmUsageOut,
  MarketingSpendCreate,
  MarketingSpendRow,
  MetricsCohortsOut,
  MetricsEconomicsOut,
  MetricsFunnelOut,
  MetricsOverviewOut,
  OneTimeMonthlyOut,
  PromoPerformanceOut,
  ReportOptionsAnalyticsOut,
  SubscriptionListOut,
  SubscriptionsOverviewOut,
} from '@/types/admin'

export async function fetchMetricsOverview(params: { period?: string } = {}) {
  const { data } = await api.get<MetricsOverviewOut>('/api/v1/admin/metrics/overview', { params })
  return data
}

export async function fetchMetricsFunnel(params: { period?: string } = {}) {
  const { data } = await api.get<MetricsFunnelOut>('/api/v1/admin/metrics/funnel', { params })
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

export async function fetchCampaignPerformance(params: {
  date_from?: string
  date_to?: string
  group_by?: 'campaign' | 'source'
  billing_segment?: 'all' | 'one_time' | 'subscription'
}) {
  const { data } = await api.get<CampaignPerformanceOut>('/api/v1/admin/metrics/campaign-performance', {
    params,
  })
  return data
}

export async function fetchOneTimeMonthly(params: { months?: number } = {}) {
  const { data } = await api.get<OneTimeMonthlyOut>('/api/v1/admin/metrics/one-time-monthly', { params })
  return data
}

export async function fetchReportOptionsAnalytics() {
  const { data } = await api.get<ReportOptionsAnalyticsOut>('/api/v1/admin/metrics/report-options-analytics')
  return data
}

export async function fetchPromoPerformance() {
  const { data } = await api.get<PromoPerformanceOut>('/api/v1/admin/metrics/promo-performance')
  return data
}

export async function fetchSubscriptionsOverview(params: { months?: number } = {}) {
  const { data } = await api.get<SubscriptionsOverviewOut>('/api/v1/admin/metrics/subscriptions-overview', {
    params,
  })
  return data
}

export async function fetchSubscriptionsList(params: { limit?: number } = {}) {
  const { data } = await api.get<SubscriptionListOut>('/api/v1/admin/metrics/subscriptions-list', { params })
  return data
}

export async function fetchLlmUsage(params: { date_from?: string; date_to?: string } = {}) {
  const { data } = await api.get<LlmUsageOut>('/api/v1/admin/metrics/llm-usage', { params })
  return data
}

export async function fetchLlmMargin() {
  const { data } = await api.get<LlmMarginOut>('/api/v1/admin/metrics/llm-margin')
  return data
}
