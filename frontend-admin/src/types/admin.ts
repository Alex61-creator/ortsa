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
  tariff_code?: string | null
  payment_provider?: string | null
  payment_id?: string | null
  promo_code?: string | null
  refunded_amount?: string
  created_at: string
}

export interface AdminTaskRow {
  id: string
  queue: string
  name: string
  status: string
  created_at: string
  updated_at: string
  worker?: string | null
  error?: string | null
}

export interface PromoRow {
  id: string
  code: string
  discount_percent: number
  max_uses: number
  used_count: number
  active_until: string | null
  is_active: boolean
  created_at?: string | null
  created_by?: string | null
}

export interface FeatureFlagRow {
  key: string
  description: string
  enabled: boolean
  updated_at?: string | null
  updated_by?: string | null
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
  details?: Record<string, unknown> | null
}

export interface AdminOrderTimelineItem {
  type: "analytics" | "admin_log"
  time: string
  event_name?: string | null
  action?: string | null
  entity?: string | null
  details?: Record<string, unknown> | null
}

export interface MarketingSpendRow {
  id: number
  period_start: string
  period_end: string
  channel: string
  campaign_name: string | null
  spend_amount: string
  currency: string
  notes: string | null
  created_by: string | null
  created_at: string
}

export interface MarketingSpendCreate {
  period_start: string
  period_end: string
  channel: string
  campaign_name?: string | null
  spend_amount: string
  currency?: string
  notes?: string | null
}

export interface MetricValueCard {
  key: string
  label: string
  value: number
  previous_value?: number | null
  delta_pct?: number | null
  unit?: string | null
  status?: string | null
  hint?: string | null
}

export interface MetricsOverviewOut {
  period_start: string
  period_end: string
  cards: MetricValueCard[]
  alerts: string[]
}

export interface ChannelCacRow {
  channel: string
  spend: number
  first_paid_users: number
  cac: number
}

export interface CohortRow {
  cohort: string
  size: number
  m1: number
  m3: number
  m6: number
}

export interface MetricsCohortsOut {
  period_start: string
  period_end: string
  rows: CohortRow[]
}

export interface MetricsEconomicsOut {
  period_start: string
  period_end: string
  blended_cac: number
  ltv_cac: number
  contribution_margin: number
  aov: number
  attach_rate: number
  channel_cac: ChannelCacRow[]
  action_hints: string[]
}

export interface SynastryOverrideRow {
  user_id: number
  synastry_enabled: boolean
  free_synastries_granted: number
  admin_note: string | null
  created_at: string
  updated_at: string
}

export interface AdminSynastryReportRow {
  id: number
  natal_data_id_1: number
  natal_data_id_2: number
  person1_name: string | null
  person2_name: string | null
  status: string
  generation_count: number
  pdf_ready: boolean
  created_at: string
  updated_at: string
}

export interface AppSettingRow {
  key: string
  value: string
  description: string | null
  updated_at: string
}
