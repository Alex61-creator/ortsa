"""
Зафиксированные варианты продукта для набора отчётов и подарка (Phase 2 дорожной карты).

Реализация в коде заказов/оплаты — только после утверждённого ТЗ. Здесь — единая точка
описания моделей, чтобы не смешивать их с текущей логикой одного заказа = один отчёт.

BUNDLE_OPTION_A — один заказ `bundle` с полями списка `natal_data_id` (или очередь задач).
BUNDLE_OPTION_B — один платёж, три независимых заказа, связанных `payment_group_id`.
BUNDLE_OPTION_C — баланс «кредитов отчёта» на пользователе (`report_credits`), списание при генерации.

GIFT_LINK — таблица токенов: создатель, получатель (nullable до активации), срок, тариф;
публичный endpoint активации + редирект в кабинет.
"""

BUNDLE_OPTION_A = "single_order_multi_natal_queue"
BUNDLE_OPTION_B = "one_payment_three_orders"
BUNDLE_OPTION_C = "user_report_credits"
GIFT_LINK_MODEL = "gift_links"
