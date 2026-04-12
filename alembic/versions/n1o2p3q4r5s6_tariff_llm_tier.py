"""tariffs: llm_tier + max_natal_profiles in features

Revision ID: n1o2p3q4r5s6
Revises: m7n8o9p0q1r2
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "n1o2p3q4r5s6"
down_revision = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariffs",
        sa.Column(
            "llm_tier",
            sa.String(length=20),
            nullable=False,
            server_default="natal_full",
        ),
    )
    op.alter_column("tariffs", "llm_tier", server_default=None)

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE tariffs SET llm_tier = CASE code
                WHEN 'free' THEN 'free'
                WHEN 'report' THEN 'natal_full'
                WHEN 'bundle' THEN 'natal_full'
                WHEN 'pro' THEN 'pro'
                ELSE 'natal_full'
            END
            """
        )
    )

    # Добавляем max_natal_profiles в JSON features (PostgreSQL: json -> jsonb merge)
    conn.execute(
        sa.text(
            """
            UPDATE tariffs SET features = (
                COALESCE(features::text, '{}')::jsonb
                || jsonb_build_object(
                    'max_natal_profiles',
                    CASE code
                        WHEN 'free' THEN 1
                        WHEN 'report' THEN 1
                        WHEN 'bundle' THEN 3
                        WHEN 'pro' THEN 5
                        ELSE 1
                    END
                )
            )::json
            """
        )
    )


def downgrade() -> None:
    op.drop_column("tariffs", "llm_tier")
