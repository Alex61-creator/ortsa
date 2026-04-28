"""forecast fields: orders, reports, subscriptions + tariff features update

Revision ID: b1c2d3e4f5g6
Revises: z9y8x7w6v5u4
Create Date: 2026-04-26

Добавляет:
- orders.forecast_window_start / forecast_window_end
- reports.report_type (natal | forecast | synastry)
- subscriptions.next_forecast_at / last_forecast_at
- Обновляет tariffs.features для sub_monthly, sub_annual, transit_month_pack
- Добавляет тариф forecast_month_pack
"""

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5g6"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── orders: поля окна прогноза ────────────────────────────────────────────
    op.add_column("orders", sa.Column("forecast_window_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("forecast_window_end", sa.DateTime(timezone=True), nullable=True))

    # ── reports: тип отчёта ───────────────────────────────────────────────────
    op.add_column(
        "reports",
        sa.Column("report_type", sa.String(20), nullable=False, server_default="natal"),
    )

    # ── subscriptions: scheduling forecast ────────────────────────────────────
    op.add_column("subscriptions", sa.Column("next_forecast_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("last_forecast_at", sa.DateTime(timezone=True), nullable=True))

    # ── Обновляем features подписок: включаем transits + progressions ─────────
    op.execute(
        """
        UPDATE tariffs
        SET features = jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(features, '{}'),
                        '{includes_transits}', 'true'
                    ),
                    '{includes_progressions}', 'true'
                ),
                '{forecast_window_days}', '30'
            ),
            '{monthly_generation_enabled}', 'true'
        )
        WHERE code IN ('sub_monthly', 'sub_annual')
        """
    )

    # ── Обновляем transit_month_pack: включаем forecast features, llm_tier=pro ─
    op.execute(
        """
        UPDATE tariffs
        SET
            features = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(features, '{}'),
                        '{includes_transits}', 'true'
                    ),
                    '{includes_progressions}', 'true'
                ),
                '{forecast_window_days}', '30'
            ),
            llm_tier = 'pro'
        WHERE code = 'transit_month_pack'
        """
    )

    # ── Добавляем forecast_month_pack (новый add-on) ───────────────────────────
    op.execute(
        """
        INSERT INTO tariffs
            (code, name, price, price_usd, features, retention_days, billing_type, llm_tier, priority)
        VALUES
            (
                'forecast_month_pack',
                'Forecast month pack',
                590.00,
                7.00,
                '{
                    "is_addon": true,
                    "addon_requires_tariff_codes": ["report", "bundle"],
                    "addon_offer_ttl_hours": 72,
                    "addon_repeat_limit": 3,
                    "includes_transits": true,
                    "includes_progressions": true,
                    "forecast_window_days": 30
                }',
                30,
                'one_time',
                'pro',
                96
            )
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM tariffs WHERE code = 'forecast_month_pack'")
    op.execute(
        """
        UPDATE tariffs
        SET llm_tier = 'natal_full',
            features = features - 'includes_transits' - 'includes_progressions' - 'forecast_window_days'
        WHERE code = 'transit_month_pack'
        """
    )
    op.execute(
        """
        UPDATE tariffs
        SET features = features
            - 'includes_transits'
            - 'includes_progressions'
            - 'forecast_window_days'
            - 'monthly_generation_enabled'
        WHERE code IN ('sub_monthly', 'sub_annual')
        """
    )
    op.drop_column("subscriptions", "last_forecast_at")
    op.drop_column("subscriptions", "next_forecast_at")
    op.drop_column("reports", "report_type")
    op.drop_column("orders", "forecast_window_end")
    op.drop_column("orders", "forecast_window_start")
