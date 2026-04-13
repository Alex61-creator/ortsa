export interface TariffSummary {
  code: string
  name: string
}

export interface AdminOrderRow {
  id: number
  user_id: number
  status: string
  amount: string
  natal_data_id: number | null
  created_at: string
  updated_at: string
  tariff: TariffSummary
  report_ready: boolean
}

export interface AdminUserRow {
  id: number
  email: string
  oauth_provider: string
  is_admin: boolean
  created_at: string
  consent_given_at: string | null
}

export interface AdminUserDetail extends AdminUserRow {
  external_id: string
}

export interface TariffRow {
  id: number
  code: string
  name: string
  price: string
  price_usd: string
  compare_price_usd: string | null
  annual_total_usd: string | null
  features: Record<string, unknown>
  retention_days: number
  priority: number
  billing_type: string
  subscription_interval: string | null
  llm_tier: string
}

export type TariffPatch = Partial<{
  name: string
  price: string
  price_usd: string
  compare_price_usd: string | null
  annual_total_usd: string | null
  features: Record<string, unknown>
  retention_days: number
  priority: number
  billing_type: string
  subscription_interval: string | null
  llm_tier: string
}>

export interface DashboardSummary {
  order_metrics: {
    failed_orders_total: number
    processing_stuck_over_2h: number
    checked_at: string
  }
  analytics_stub: boolean
  future_docs: string
}

export interface RetryReportResponse {
  order_id: number
  status: string
  queued: boolean
}

export interface RefundResponse {
  refund_id: string
  status: string
  amount: string
}
