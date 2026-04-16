"""retention cleanup foundation

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "e6f7g8h9i0j1"
down_revision = "d5e6f7g8h9i0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_natal_data_user_created_at", "natal_data", ["user_id", "created_at"], unique=False)
    op.create_index("ix_order_natal_items_order_slot", "order_natal_items", ["order_id", "slot_index"], unique=False)

    op.add_column(
        "synastry_reports",
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "synastry_reports",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE tariffs
        SET retention_days = CASE code
            WHEN 'free' THEN 3
            WHEN 'report' THEN 30
            WHEN 'bundle' THEN 30
            WHEN 'sub_monthly' THEN 180
            WHEN 'sub_annual' THEN 180
            WHEN 'pro' THEN 180
            ELSE retention_days
        END
        """
    )


def downgrade() -> None:
    op.drop_column("synastry_reports", "expires_at")
    op.drop_column("synastry_reports", "retention_days")
    op.drop_index("ix_order_natal_items_order_slot", table_name="order_natal_items")
    op.drop_index("ix_natal_data_user_created_at", table_name="natal_data")
