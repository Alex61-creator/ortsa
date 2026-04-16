"""order_idempotency: идемпотентность POST /orders

Revision ID: b3c4d5e6f7g8
Revises: u1v2w3x4y5z6
Create Date: 2026-04-16

Таблица хранит lifecycle идемпотентности для HTTP-запросов create_order,
чтобы повторные клики/ретраи не создавали дубликаты заказов и платежей.
"""

from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7g8"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    state_enum = sa.Enum("processing", "completed", "failed", name="orderidempotencystate")

    op.create_table(
        "order_idempotency",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("state", state_enum, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("yookassa_id", sa.String(length=100), nullable=True),
        sa.Column("confirmation_url", sa.String(length=500), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_order_idempotency_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_idempotency_order_id_orders"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_idempotency")),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_order_idempotency_user_idempotency_key",
        ),
    )

    op.create_index("ix_order_idempotency_user_id", "order_idempotency", ["user_id"], unique=False)
    op.create_index("ix_order_idempotency_state", "order_idempotency", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_idempotency_state", table_name="order_idempotency")
    op.drop_index("ix_order_idempotency_user_id", table_name="order_idempotency")
    op.drop_table("order_idempotency")

