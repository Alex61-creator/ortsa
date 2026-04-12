"""orders: natal_data_id FK

Revision ID: a1b2c3d4e5f6
Revises: 9988e2bb8d73
Create Date: 2026-04-11

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "9988e2bb8d73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("natal_data_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_orders_natal_data_id_natal_data"),
        "orders",
        "natal_data",
        ["natal_data_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_orders_natal_data_id_natal_data"), "orders", type_="foreignkey")
    op.drop_column("orders", "natal_data_id")
