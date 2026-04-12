"""orders: optional report_delivery_email for PDF delivery

Revision ID: m7n8o9p0q1r2
Revises: h1i2j3k4l5m6
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "m7n8o9p0q1r2"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("report_delivery_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "report_delivery_email")
