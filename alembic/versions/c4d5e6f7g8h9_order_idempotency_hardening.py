"""order_idempotency_hardening: fingerprint + processing lease

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7g8h9"
down_revision = "b3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_idempotency",
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "order_idempotency",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Для старых записей не знаем реальный payload, но пустых fingerprint в прод не допускаем.
    op.execute("UPDATE order_idempotency SET request_fingerprint = '' WHERE request_fingerprint IS NULL")
    op.alter_column("order_idempotency", "request_fingerprint", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    op.drop_column("order_idempotency", "processing_started_at")
    op.drop_column("order_idempotency", "request_fingerprint")

