"""orders.report_option_flags JSON for report/bundle upsell toggles

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("report_option_flags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "report_option_flags")
