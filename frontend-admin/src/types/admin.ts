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
  promo_code?: string | null
  report_option_flags?: Record<string, boolean> | null
  report_options_line_amount?: string | null
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

export interface MonthAmountPoint {
  month: string
  amount_rub: number
}

export interface TariffKpiRow {
  tariff_code: string
  tariff_name: string
  revenue_rub: number
  ai_cost_rub: number
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
    revenue_90d_rub?: number
    refunds_lifetime_rub?: number
  }
  llm_metrics?: {
    llm_cost: number
    roi_pct: number
    avg_report_cost: number
    infra_cost_rub?: number
    payment_fee_rub?: number
    variable_cost_rub?: number
    contribution_margin_pct?: number
  }
  mrr_history?: MrrPoint[]
  ai_cost_history?: MonthAmountPoint[]
  tariff_kpis?: TariffKpiRow[]
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
  methodology: string
}

export interface MetricsFunnelOut {
  period_start: string
  period_end: string
  steps: FunnelStep[]
  methodology: string
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
  methodology: string
}

export interface CampaignPerformanceRow {
  segment_key: string
  signups: number
  first_paid_users: number
  first_paid_revenue_rub: number
  orders_completed: number
  cr1: number
}

export interface CampaignPerformanceOut {
  period_start: string
  period_end: string
  group_by: string
  billing_segment: string
  methodology: string
  rows: CampaignPerformanceRow[]
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
  methodology: string
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

export interface OneTimeMonthRow {
  month: string
  orders_count: number
  revenue_rub: number
  aov_rub: number
}

export interface OneTimeMonthlyOut {
  methodology: string
  rows: OneTimeMonthRow[]
}

export interface ReportOptionsAnalyticsOut {
  methodology: string
  key_counts: Record<string, number>
  bucket_counts: Record<string, number>
  estimated_options_revenue_rub: number
  orders_sampled: number
}

export interface PromoPerformanceRow {
  promocode: string
  redemptions: number
  discount_total_rub: number
  order_revenue_rub: number
}

export interface PromoPerformanceOut {
  methodology: string
  rows: PromoPerformanceRow[]
}

export interface SubscriptionMonthRow {
  month: string
  new_subscriptions: number
  first_payment_orders: number
  subscription_order_revenue_rub: number
  renewal_revenue_rub: number
}

export interface SubscriptionsOverviewOut {
  methodology: string
  active_subscriptions_now: number
  monthly_rows: SubscriptionMonthRow[]
}

export interface SubscriptionExportRow {
  id: number
  user_id: number
  tariff_code: string
  status: string
  current_period_start: string | null
  current_period_end: string | null
  created_at: string
}

export interface SubscriptionListOut {
  rows: SubscriptionExportRow[]
}
