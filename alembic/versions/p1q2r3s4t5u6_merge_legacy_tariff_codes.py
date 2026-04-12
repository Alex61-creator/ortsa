"""Удаление кодов standard/premium: слияние в report/pro

Revision ID: p1q2r3s4t5u6
Revises: o1p2q3r4s5t6
Create Date: 2026-04-12

"""

from alembic import op
import sqlalchemy as sa


revision = "p1q2r3s4t5u6"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DO $$
            DECLARE
                sid int;
                rid int;
            BEGIN
                SELECT id INTO sid FROM tariffs WHERE code = 'standard' LIMIT 1;
                SELECT id INTO rid FROM tariffs WHERE code = 'report' LIMIT 1;
                IF sid IS NOT NULL THEN
                    IF rid IS NOT NULL AND sid <> rid THEN
                        UPDATE orders SET tariff_id = rid WHERE tariff_id = sid;
                        UPDATE subscriptions SET tariff_id = rid WHERE tariff_id = sid;
                        DELETE FROM tariffs WHERE id = sid;
                    ELSIF rid IS NULL THEN
                        UPDATE tariffs SET code = 'report', llm_tier = 'natal_full'
                        WHERE id = sid;
                    END IF;
                END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            DECLARE
                pid int;
                prid int;
            BEGIN
                SELECT id INTO pid FROM tariffs WHERE code = 'premium' LIMIT 1;
                SELECT id INTO prid FROM tariffs WHERE code = 'pro' LIMIT 1;
                IF pid IS NOT NULL THEN
                    IF prid IS NOT NULL AND pid <> prid THEN
                        UPDATE orders SET tariff_id = prid WHERE tariff_id = pid;
                        UPDATE subscriptions SET tariff_id = prid WHERE tariff_id = pid;
                        DELETE FROM tariffs WHERE id = pid;
                    ELSIF prid IS NULL THEN
                        UPDATE tariffs SET code = 'pro', llm_tier = 'pro'
                        WHERE id = pid;
                    END IF;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    pass
