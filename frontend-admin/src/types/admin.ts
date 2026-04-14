export interface TariffSummary {
  code: string
  name: string
  billing_type: string
  subscription_interval: string | null
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
  // Enriched fields from backend
  total_spent: string
  orders_count: number
  last_order_at: string | null
  blocked: boolean
  latest_tariff_name: string | null
  latest_tariff_code: string | null
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

export interface MrrPoint {
  month: string
  mrr: number
}

export interface DashboardSummary {
  order_metrics: {
    failed_orders_total: number
    processing_stuck_over_2h: number
    checked_at: string
  }
  analytics_stub?: boolean
  future_docs?: string
  business_metrics?: {
    users_total: number
    mrr: number
    new_mrr: number
    churn_mrr: number
    ltv: number
  }
  llm_metrics?: {
    llm_cost: number
    roi_pct: number
    avg_report_cost: number
    tokens_total: number
  }
  mrr_history?: MrrPoint[]
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

export interface FunnelStep {
  key: string
  title: string
  count: number
  conversion_pct: number
}

export interface FunnelSummary {
  period: string
  steps: FunnelStep[]
  drop_offs?: Array<{
    from_key: string
    to_key: string
    lost: number
  }>
  recommendations?: string[]
}

export interface AdminPaymentRow {
  order_id: number
  user_id: number
  user_email: string
  status: string
  amount: string
  tariff_name: string
  created_at: string
}

export interface AdminTaskRow {
  id: string
  queue: string
  name: string
  status: string
  created_at: string
  updated_at: string
}

export interface PromoRow {
  id: string
  code: string
  discount_percent: number
  max_uses: number
  used_count: number
  active_until: string | null
  is_active: boolean
}

export interface FeatureFlagRow {
  key: string
  description: string
  enabled: boolean
}

export interface HealthWidget {
  name: string
  status: string
  value: string
}

export interface AdminLogRow {
  id: string
  actor_email: string
  action: string
  entity: string
  created_at: string
}
