"""subscriptions: current_period_start

Revision ID: r3s4t5u6v7w8
Revises: p1q2r3s4t5u6
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "r3s4t5u6v7w8"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE subscriptions
            SET current_period_start = current_period_end - INTERVAL '30 days'
            WHERE current_period_end IS NOT NULL AND current_period_start IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "current_period_start")
