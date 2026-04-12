"""token_version on users; orderstatus failed_to_init_payment

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11

"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("users", "token_version", server_default=None)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Значение должно совпадать с OrderStatus.FAILED_TO_INIT_PAYMENT.value
        op.execute(sa.text("ALTER TYPE orderstatus ADD VALUE 'failed_to_init_payment'"))


def downgrade() -> None:
    op.drop_column("users", "token_version")
    # PostgreSQL: removing an enum value requires recreating the type; omit for safety.
