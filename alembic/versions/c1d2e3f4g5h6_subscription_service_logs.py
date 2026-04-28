"""Subscription service logs: monthly_forecast, weekly_digest, annual_progression

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6, b2c3d4e5f6g7
Create Date: 2026-04-28

Merge двух голов и добавляет таблицы идемпотентности:
  - monthly_forecast_logs   (subscription_id + period_yyyymm, UNIQUE)
  - weekly_digest_logs      (subscription_id + week_start, UNIQUE)
  - annual_progression_logs (subscription_id + year, UNIQUE)
"""

from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4g5h6"
down_revision = ("b1c2d3e4f5g6", "b2c3d4e5f6g7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── monthly_forecast_logs ────────────────────────────────────────────────
    op.create_table(
        "monthly_forecast_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_id",
            sa.Integer,
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_yyyymm", sa.String(7), nullable=False, comment="Формат: 2026-04"),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.UniqueConstraint("subscription_id", "period_yyyymm", name="uq_forecast_sub_period"),
    )
    op.create_index(
        "ix_monthly_forecast_logs_subscription_id",
        "monthly_forecast_logs",
        ["subscription_id"],
    )

    # ── weekly_digest_logs ───────────────────────────────────────────────────
    op.create_table(
        "weekly_digest_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_id",
            sa.Integer,
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date, nullable=False, comment="Понедельник недели"),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("subscription_id", "week_start", name="uq_weekly_sub_week"),
    )
    op.create_index(
        "ix_weekly_digest_logs_subscription_id",
        "weekly_digest_logs",
        ["subscription_id"],
    )

    # ── annual_progression_logs ──────────────────────────────────────────────
    op.create_table(
        "annual_progression_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_id",
            sa.Integer,
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer, nullable=False, comment="Год жизни пользователя"),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.UniqueConstraint("subscription_id", "year", name="uq_progression_sub_year"),
    )
    op.create_index(
        "ix_annual_progression_logs_subscription_id",
        "annual_progression_logs",
        ["subscription_id"],
    )


def downgrade() -> None:
    op.drop_table("annual_progression_logs")
    op.drop_table("weekly_digest_logs")
    op.drop_table("monthly_forecast_logs")
