from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FunnelStep(BaseModel):
    key: str
    title: str
    count: int
    conversion_pct: float


class FunnelSummary(BaseModel):
    period: str
    steps: list[FunnelStep]
    drop_offs: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AdminPaymentRow(BaseModel):
    order_id: int
    user_id: int
    user_email: str
    status: str
    amount: Decimal
    tariff_name: str
    tariff_code: str | None = None
    payment_provider: str | None = None
    payment_id: str | None = None
    promo_code: str | None = None
    refunded_amount: Decimal = Decimal("0.00")
    created_at: datetime


class AdminTaskRow(BaseModel):
    id: str
    queue: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    worker: str | None = None
    error: str | None = None


class PromoOut(BaseModel):
    id: str
    code: str
    discount_percent: int = Field(ge=1, le=100)
    max_uses: int = Field(ge=1)
    used_count: int = Field(ge=0)
    active_until: Optional[datetime] = None
    is_active: bool
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class PromoCreate(BaseModel):
    code: str
    discount_percent: int = Field(ge=1, le=100)
    max_uses: int = Field(ge=1, default=100)
    active_until: Optional[datetime] = None


class PromoPatch(BaseModel):
    discount_percent: Optional[int] = Field(default=None, ge=1, le=100)
    max_uses: Optional[int] = Field(default=None, ge=1)
    active_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class FlagOut(BaseModel):
    key: str
    description: str
    enabled: bool
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class FlagPatch(BaseModel):
    enabled: bool
    reason: Optional[str] = None


class HealthWidget(BaseModel):
    name: str
    status: str
    value: str


class AdminLogRow(BaseModel):
    id: str
    actor_email: str
    action: str
    entity: str
    created_at: datetime
    details: dict | None = None

    class Config:
        from_attributes = True


class AdminOrderTimelineItem(BaseModel):
    type: Literal["analytics", "admin_log"]
    time: datetime
    event_name: str | None = None
    action: str | None = None
    entity: str | None = None
    details: dict | None = None


class MarketingSpendCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    channel: str
    campaign_name: Optional[str] = None
    spend_amount: Decimal = Field(ge=0)
    currency: str = "RUB"
    notes: Optional[str] = None


class MarketingSpendRow(MarketingSpendCreate):
    id: int
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MetricValueCard(BaseModel):
    key: str
    label: str
    value: float
    previous_value: float | None = None
    delta_pct: float | None = None
    unit: str | None = None
    status: str | None = None
    hint: str | None = None


class ChannelCacRow(BaseModel):
    channel: str
    spend: float
    first_paid_users: int
    cac: float


class CohortRow(BaseModel):
    cohort: str
    size: int
    m1: float
    m3: float
    m6: float


class MetricsOverviewOut(BaseModel):
    period_start: datetime
    period_end: datetime
    cards: list[MetricValueCard]
    alerts: list[str] = Field(default_factory=list)
    methodology: str = "event_based"


class MetricsFunnelOut(BaseModel):
    period_start: datetime
    period_end: datetime
    steps: list[FunnelStep]
    methodology: str = "event_based"


class MetricsCohortsOut(BaseModel):
    period_start: datetime
    period_end: datetime
    rows: list[CohortRow]
    methodology: str = "event_based"


class MetricsEconomicsOut(BaseModel):
    period_start: datetime
    period_end: datetime
    blended_cac: float
    ltv_cac: float
    contribution_margin: float
    aov: float
    attach_rate: float
    channel_cac: list[ChannelCacRow]
    action_hints: list[str] = Field(default_factory=list)
    methodology: str = "event_based"


class UserNoteOut(BaseModel):
    id: str
    text: str
    created_at: datetime


class UserNoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class TariffHistoryRow(BaseModel):
    id: str
    tariff_id: int
    actor: str
    payload: dict
    created_at: datetime


class AddonOfferDispatchRow(BaseModel):
    id: int
    user_id: int
    parent_order_id: int
    addon_code: str
    channel: str
    attempt_no: int
    scheduled_at: datetime
    sent_at: datetime | None = None
    status: str
    skip_reason: str | None = None
    dedupe_key: str
    payload: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignPerformanceRow(BaseModel):
    segment_key: str
    signups: int
    first_paid_users: int
    first_paid_revenue_rub: float
    orders_completed: int
    cr1: float


class CampaignPerformanceOut(BaseModel):
    period_start: datetime
    period_end: datetime
    group_by: str
    billing_segment: str
    methodology: str
    rows: list[CampaignPerformanceRow]


class OneTimeMonthRow(BaseModel):
    month: str
    orders_count: int
    revenue_rub: float
    aov_rub: float


class OneTimeMonthlyOut(BaseModel):
    methodology: str
    rows: list[OneTimeMonthRow]


class ReportOptionsAnalyticsOut(BaseModel):
    methodology: str
    key_counts: dict[str, int]
    bucket_counts: dict[str, int]
    estimated_options_revenue_rub: float
    orders_sampled: int


class PromoPerformanceRow(BaseModel):
    promocode: str
    redemptions: int
    discount_total_rub: float
    order_revenue_rub: float


class PromoPerformanceOut(BaseModel):
    methodology: str
    rows: list[PromoPerformanceRow]


class SubscriptionMonthRow(BaseModel):
    month: str
    new_subscriptions: int
    first_payment_orders: int
    subscription_order_revenue_rub: float
    renewal_revenue_rub: float


class SubscriptionsOverviewOut(BaseModel):
    methodology: str
    active_subscriptions_now: int
    monthly_rows: list[SubscriptionMonthRow]


class SubscriptionExportRow(BaseModel):
    id: int
    user_id: int
    tariff_code: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    created_at: datetime


class SubscriptionListOut(BaseModel):
    rows: list[SubscriptionExportRow]


# ── LLM аналитика ─────────────────────────────────────────────────────────────

class LlmProviderUsageRow(BaseModel):
    provider: str
    calls_count: int
    cost_rub: float
    cached_tokens: int
    pct_of_total: float


class LlmUsageOut(BaseModel):
    period_start: datetime
    period_end: datetime
    rows: list[LlmProviderUsageRow]
    most_used_provider: str | None = None
    total_calls: int
    total_cost_rub: float


class LlmMarginRow(BaseModel):
    provider: str
    revenue_rub: float
    ai_cost_rub: float
    margin_rub: float
    margin_pct: float


class LlmMarginOut(BaseModel):
    current_month: list[LlmMarginRow]
    total: list[LlmMarginRow]


# ── LLM настройки провайдеров ─────────────────────────────────────────────────

class LlmProviderConfig(BaseModel):
    provider: str
    enabled: bool
    order_index: int


class LlmProvidersOut(BaseModel):
    providers: list[LlmProviderConfig]
    fallback_order: list[str]


class LlmProviderToggleIn(BaseModel):
    enabled: bool


class LlmFallbackOrderIn(BaseModel):
    order: list[str]  # e.g. ["claude", "grok", "deepseek"]

