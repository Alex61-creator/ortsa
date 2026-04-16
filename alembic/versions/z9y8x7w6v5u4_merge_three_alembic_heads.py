"""merge three alembic heads (mainline, orders_indexes, synastry_addon branch)

Revision ID: z9y8x7w6v5u4
Revises: g2h3i4j5k6l7, s4t5u6v7w8x9, v7w8x9y0z1a2
Create Date: 2026-04-16

Сводит ветки после исправления дублирующегося revision id у synastry_addon.
"""

from alembic import op

revision = "z9y8x7w6v5u4"
down_revision = ("g2h3i4j5k6l7", "s4t5u6v7w8x9", "v7w8x9y0z1a2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
