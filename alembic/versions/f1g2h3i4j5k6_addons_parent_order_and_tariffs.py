"""addons parent order and tariffs

Revision ID: f1g2h3i4j5k6
Revises: e6f7g8h9i0j1
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "f1g2h3i4j5k6"
down_revision = "e6f7g8h9i0j1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("parent_order_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_orders_parent_order_id_orders",
        "orders",
        "orders",
        ["parent_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_parent_order_id", "orders", ["parent_order_id"], unique=False)

    op.execute(
        """
        INSERT INTO tariffs
            (code, name, price, price_usd, features, retention_days, billing_type, llm_tier, priority)
        VALUES
            (
                'transit_month_pack',
                'Transit month pack',
                590.00,
                7.00,
                '{"is_addon": true, "addon_requires_tariff_codes": ["report", "bundle", "sub_monthly", "sub_annual", "pro"], "addon_offer_ttl_hours": 72, "addon_repeat_limit": 1}',
                30,
                'one_time',
                'natal_full',
                95
            ),
            (
                'compatibility_deep_dive',
                'Compatibility deep dive',
                1490.00,
                18.00,
                '{"is_addon": true, "addon_requires_tariff_codes": ["bundle", "sub_monthly", "sub_annual", "pro", "synastry_addon"], "addon_offer_ttl_hours": 72, "addon_repeat_limit": 1}',
                30,
                'one_time',
                'natal_full',
                94
            ),
            (
                'return_pack',
                'Return pack',
                1990.00,
                24.00,
                '{"is_addon": true, "addon_requires_tariff_codes": ["report", "bundle", "sub_monthly", "sub_annual", "pro"], "addon_offer_ttl_hours": 168, "addon_repeat_limit": 1}',
                180,
                'one_time',
                'natal_full',
                93
            )
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM tariffs WHERE code IN ('transit_month_pack', 'compatibility_deep_dive', 'return_pack')"
    )
    op.drop_index("ix_orders_parent_order_id", table_name="orders")
    op.drop_constraint("fk_orders_parent_order_id_orders", "orders", type_="foreignkey")
    op.drop_column("orders", "parent_order_id")
