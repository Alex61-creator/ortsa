# Analytics Event Schema

Статус: `v1`

## Канонические события

- `signup_completed`
- `first_purchase_completed`
- `order_completed`
- `addon_attached`
- `addon_purchase_started`
- `addon_purchase_completed`
- `addon_purchase_blocked`
- `cohort_month_started`
- `refund_completed`
- `acquisition_cost_recorded`

## Runtime events

- `subscription_renewal_payment`

- `order_created`
- `payment_started`
- `payment_succeeded`
- `report_generation_started`
- `report_generation_completed`
- `report_generation_failed`
- `addon_report_generation_started`
- `addon_report_generation_completed`
- `addon_report_generation_failed`
- `addon_offer_shown`
- `addon_offer_email_sent`
- `addon_offer_push_sent`
- `addon_offer_email_scheduled`
- `addon_offer_push_scheduled`
- `addon_offer_suppressed`
- `addon_offer_send_failed`
- `email_sent`

## Обязательные поля

- `user_id`
- `order_id`
- `tariff_code`
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `source_channel`
- `event_time`
- `amount`
- `cost_components`
- `correlation_id`

## Правила расчёта

- Таймзона: `UTC`
- Атрибуция: `last touch` по `utm_source`, fallback в `source_channel`
- Дедупликация: через `dedupe_key`
- Refund/chargeback: учитываются в `refund_completed` и в unit economics

## KPI formulas v1

- `CR1 = users_with_first_paid_order / signed_up_users`
- `AOV = revenue_paid_orders / paid_orders_count`
- `Attach-rate add-on = orders_with_addon / eligible_base_orders`
- `Retention M1/M3/M6 = active_users_in_month_N / cohort_size_month_0`
- `Blended CAC = sum(spend in P) / count(first_paid_users in P)`
- `Channel CAC = sum(spend[channel] in P) / count(first_paid_users[channel] in P)`
- `LTV/CAC = lifetime_gross_profit_per_user / acquisition_cost_per_user`
- `Contribution Margin = (Revenue - VariableCosts - PaymentFees - AI/InfraCost - Refunds) / Revenue`
