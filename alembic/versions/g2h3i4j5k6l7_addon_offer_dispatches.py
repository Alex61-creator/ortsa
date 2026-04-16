"""addon offer dispatches

Revision ID: g2h3i4j5k6l7
Revises: f1g2h3i4j5k6
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "g2h3i4j5k6l7"
down_revision = "f1g2h3i4j5k6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "addon_offer_dispatches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_order_id", sa.Integer(), nullable=False),
        sa.Column("addon_code", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("skip_reason", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(
        "ix_addon_offer_dispatch_user_parent_addon",
        "addon_offer_dispatches",
        ["user_id", "parent_order_id", "addon_code"],
        unique=False,
    )
    op.create_index(
        "ix_addon_offer_dispatch_status_scheduled_at",
        "addon_offer_dispatches",
        ["status", "scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_addon_offer_dispatch_status_scheduled_at", table_name="addon_offer_dispatches")
    op.drop_index("ix_addon_offer_dispatch_user_parent_addon", table_name="addon_offer_dispatches")
    op.drop_table("addon_offer_dispatches")
