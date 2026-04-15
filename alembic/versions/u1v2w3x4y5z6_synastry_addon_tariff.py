"""synastry_addon_tariff: добавляет служебный тариф для платной синастрии

Revision ID: u1v2w3x4y5z6
Revises: t1u2v3w4x5y6
Create Date: 2026-04-15

Добавляет тариф synastry_addon (190 руб.) — используется для оплаты
дополнительных синастрий сверх включённых в основной тариф.
"""

import sqlalchemy as sa
from alembic import op

revision = "u1v2w3x4y5z6"
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
