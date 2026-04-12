"""monthly_digest_logs for Pro monthly email idempotency

Revision ID: o1p2q3r4s5t6
Revises: n1o2p3q4r5s6
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "o1p2q3r4s5t6"
down_revision = "n1o2p3q4r5s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monthly_digest_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("period_yyyymm", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
            name=op.f("fk_monthly_digest_logs_subscription_id_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_digest_logs")),
        sa.UniqueConstraint("subscription_id", "period_yyyymm", name="uq_digest_sub_period"),
    )


def downgrade() -> None:
    op.drop_table("monthly_digest_logs")
