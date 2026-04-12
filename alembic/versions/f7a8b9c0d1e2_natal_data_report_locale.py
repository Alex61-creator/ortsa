"""natal_data report_locale for PDF/email language

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "f7a8b9c0d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "natal_data",
        sa.Column("report_locale", sa.String(length=5), nullable=False, server_default="ru"),
    )
    op.alter_column("natal_data", "report_locale", server_default=None)


def downgrade() -> None:
    op.drop_column("natal_data", "report_locale")
