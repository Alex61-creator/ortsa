"""tariffs: USD display fields for landing (EN)

Revision ID: h1i2j3k4l5m6
Revises: f7a8b9c0d1e2
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "h1i2j3k4l5m6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column("price_usd", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )
    op.add_column("tariffs", sa.Column("compare_price_usd", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("tariffs", sa.Column("annual_total_usd", sa.Numeric(precision=10, scale=2), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE tariffs SET price_usd = ROUND((price::numeric / 95.0), 2)"))
    conn.execute(
        sa.text(
            "UPDATE tariffs SET compare_price_usd = ROUND((price_usd * (2370.0 / 1590.0))::numeric, 2) "
            "WHERE code = 'bundle'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE tariffs SET annual_total_usd = ROUND((price_usd * 12)::numeric, 2) "
            "WHERE billing_type = 'subscription' OR code = 'pro'"
        )
    )

    op.alter_column("tariffs", "price_usd", server_default=None)


def downgrade() -> None:
    op.drop_column("tariffs", "annual_total_usd")
    op.drop_column("tariffs", "compare_price_usd")
    op.drop_column("tariffs", "price_usd")
