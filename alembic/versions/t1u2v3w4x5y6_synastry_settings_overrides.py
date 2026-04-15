"""synastry_settings_overrides: глобальные настройки и per-user override синастрии

Revision ID: t1u2v3w4x5y6
Revises: s1t2u3v4w5x6
Create Date: 2026-04-15

Создаёт:
- app_settings      — глобальные настройки приложения (key-value)
- user_synastry_overrides — per-user override синастрии от администратора
Начальные данные:
- synastry_repeat_price = 190.00
"""

import sqlalchemy as sa
from alembic import op

revision = "t1u2v3w4x5y6"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── app_settings ─────────────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    # Начальные настройки
    op.execute(
        "INSERT INTO app_settings (key, value, description) VALUES "
        "('synastry_repeat_price', '190.00', 'Цена повторного / дополнительного отчёта синастрии (руб.)')"
    )

    # ── user_synastry_overrides ───────────────────────────────────────────────
    op.create_table(
        "user_synastry_overrides",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("synastry_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("free_synastries_granted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_synastry_overrides")
    op.drop_table("app_settings")
