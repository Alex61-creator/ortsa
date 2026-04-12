"""tariff billing_type + subscriptions table

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column("billing_type", sa.String(length=20), nullable=False, server_default="one_time"),
    )
    op.add_column("tariffs", sa.Column("subscription_interval", sa.String(length=20), nullable=True))
    op.alter_column("tariffs", "billing_type", server_default=None)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("yookassa_payment_method_id", sa.String(length=100), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], name=op.f("fk_subscriptions_tariff_id_tariffs")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_subscriptions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )
    op.alter_column("subscriptions", "status", server_default=None)


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_column("tariffs", "subscription_interval")
    op.drop_column("tariffs", "billing_type")
