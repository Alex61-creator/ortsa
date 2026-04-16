"""synastry_addon_tariff: добавляет служебный тариф для платной синастрии

Revision ID: v7w8x9y0z1a2
Revises: t1u2v3w4x5y6
Create Date: 2026-04-15

Добавляет тариф synastry_addon (190 руб.) — используется для оплаты
дополнительных синастрий сверх включённых в основной тариф.

Примечание: ранее ошибочно использовался тот же revision id, что и у
five_tariffs_prompts_natal_items; исправлено на уникальный v7w8x9y0z1a2.
"""

import sqlalchemy as sa
from alembic import op

revision = "v7w8x9y0z1a2"
down_revision = "t1u2v3w4x5y6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO tariffs
            (code, name, price, price_usd, features, retention_days,
             billing_type, llm_tier, priority)
        VALUES
            ('synastry_addon', 'Дополнительная синастрия', 190.00, 2.00,
             '{"synastry_credits": 1}', 365,
             'one_time', 'natal_full', 99)
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM tariffs WHERE code = 'synastry_addon'")
