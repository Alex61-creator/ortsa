"""synastry_reports: таблица синастрий

Revision ID: s1t2u3v4w5x6
Revises: r3s4t5u6v7w8
Create Date: 2026-04-15

"""

from alembic import op
import sqlalchemy as sa

revision = "s1t2u3v4w5x6"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "synastry_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("natal_data_id_1", sa.Integer(), nullable=False),
        sa.Column("natal_data_id_2", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("locale", sa.String(length=5), nullable=False, server_default="ru"),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("chart_path", sa.String(length=500), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("generation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_regen_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["natal_data_id_1"], ["natal_data.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["natal_data_id_2"], ["natal_data.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "natal_data_id_1", "natal_data_id_2",
            name="uq_synastry_user_pair",
        ),
    )
    op.create_index(
        "ix_synastry_reports_user_id",
        "synastry_reports",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_synastry_reports_user_id", table_name="synastry_reports")
    op.drop_table("synastry_reports")
