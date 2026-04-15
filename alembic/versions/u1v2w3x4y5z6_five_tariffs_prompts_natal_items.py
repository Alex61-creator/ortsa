"""Пять тарифов: sub_monthly/sub_annual, таблицы llm_prompt_templates и order_natal_items

Revision ID: u1v2w3x4y5z6
Revises: p1q2r3s4t5u6
Create Date: 2026-04-14

Изменения:
- Создаёт таблицу llm_prompt_templates (редактируемые промпты LLM)
- Создаёт таблицу order_natal_items (доп. профили для тарифа bundle)
- Переименовывает тариф pro → sub_monthly
- Добавляет тариф sub_annual (годовая подписка, цена = sub_monthly * 12 * 0.66)
- Обновляет features.max_natal_profiles для всех тарифов:
    free / report → 1, bundle → 3, sub_monthly / sub_annual → 5
"""

from alembic import op
import sqlalchemy as sa

revision = "u1v2w3x4y5z6"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. llm_prompt_templates ──────────────────────────────────────────────
    op.create_table(
        "llm_prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tariff_code", sa.String(20), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.UniqueConstraint("tariff_code", "locale", name="uq_llm_prompt_code_locale"),
    )

    # ── 2. order_natal_items ─────────────────────────────────────────────────
    op.create_table(
        "order_natal_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "natal_data_id",
            sa.Integer(),
            sa.ForeignKey("natal_data.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("slot_index", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_order_natal_items_order_id",
        "order_natal_items",
        ["order_id"],
    )

    # ── 3. Переименование pro → sub_monthly + обновление max_natal_profiles ──
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                -- Переименовываем pro → sub_monthly (если sub_monthly ещё не существует)
                IF EXISTS (SELECT 1 FROM tariffs WHERE code = 'pro')
                   AND NOT EXISTS (SELECT 1 FROM tariffs WHERE code = 'sub_monthly') THEN
                    UPDATE tariffs
                    SET code = 'sub_monthly',
                        features = jsonb_set(
                            COALESCE(features::jsonb, '{}'::jsonb),
                            '{max_natal_profiles}', '5'
                        )
                    WHERE code = 'pro';
                END IF;
            END $$;
            """
        )
    )

    # ── 4. Вставка sub_annual ────────────────────────────────────────────────
    conn.execute(
        sa.text(
            """
            INSERT INTO tariffs (
                code, name, price, price_usd, compare_price_usd, annual_total_usd,
                features, retention_days, priority, billing_type, subscription_interval, llm_tier
            )
            SELECT
                'sub_annual',
                'Astro Pro (Год)',
                ROUND(price * 12 * 0.66, 2),
                ROUND(price_usd * 12 * 0.66, 2),
                NULL,
                ROUND(price * 12 * 0.66, 2),
                '{"max_natal_profiles": 5}'::jsonb,
                365,
                9,
                'subscription',
                'year',
                'pro'
            FROM tariffs
            WHERE code = 'sub_monthly'
            ON CONFLICT DO NOTHING;
            """
        )
    )

    # ── 5. Обновляем max_natal_profiles для остальных тарифов ────────────────
    conn.execute(
        sa.text(
            """
            UPDATE tariffs
            SET features = jsonb_set(
                COALESCE(features::jsonb, '{}'::jsonb),
                '{max_natal_profiles}', '1'
            )
            WHERE code IN ('free', 'report');
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE tariffs
            SET features = jsonb_set(
                COALESCE(features::jsonb, '{}'::jsonb),
                '{max_natal_profiles}', '3'
            )
            WHERE code = 'bundle';
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_order_natal_items_order_id", table_name="order_natal_items")
    op.drop_table("order_natal_items")
    op.drop_table("llm_prompt_templates")

    conn = op.get_bind()
    # Возвращаем sub_monthly → pro; удаляем sub_annual
    conn.execute(
        sa.text(
            """
            DELETE FROM tariffs WHERE code = 'sub_annual';
            UPDATE tariffs SET code = 'pro' WHERE code = 'sub_monthly';
            """
        )
    )
