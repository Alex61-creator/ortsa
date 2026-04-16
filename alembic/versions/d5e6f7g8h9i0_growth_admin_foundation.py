"""growth_admin_foundation: persistent admin config, events, spend, attribution

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "d5e6f7g8h9i0"
down_revision = "c4d5e6f7g8h9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("utm_source", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("utm_medium", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("utm_campaign", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("source_channel", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("signup_platform", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("signup_geo", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("acquisition_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_utm_source"), "users", ["utm_source"], unique=False)
    op.create_index(op.f("ix_users_source_channel"), "users", ["source_channel"], unique=False)
    op.create_index(op.f("ix_users_signup_platform"), "users", ["signup_platform"], unique=False)
    op.create_index(op.f("ix_users_signup_geo"), "users", ["signup_geo"], unique=False)

    op.add_column("orders", sa.Column("promo_code", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("payment_provider", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("variable_cost_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"))
    op.add_column("orders", sa.Column("payment_fee_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"))
    op.add_column("orders", sa.Column("ai_cost_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"))
    op.add_column("orders", sa.Column("infra_cost_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"))
    op.create_index(op.f("ix_orders_promo_code"), "orders", ["promo_code"], unique=False)

    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_action_logs")),
    )
    op.create_index(op.f("ix_admin_action_logs_actor_email"), "admin_action_logs", ["actor_email"], unique=False)
    op.create_index(op.f("ix_admin_action_logs_action"), "admin_action_logs", ["action"], unique=False)
    op.create_index(op.f("ix_admin_action_logs_entity"), "admin_action_logs", ["entity"], unique=False)
    op.create_index(op.f("ix_admin_action_logs_created_at"), "admin_action_logs", ["created_at"], unique=False)

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_feature_flags")),
    )
    op.create_table(
        "feature_flag_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flag_key", sa.String(length=100), nullable=False),
        sa.Column("previous_enabled", sa.Boolean(), nullable=False),
        sa.Column("new_enabled", sa.Boolean(), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flag_key"], ["feature_flags.key"], name=op.f("fk_feature_flag_changes_flag_key_feature_flags"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feature_flag_changes")),
    )
    op.create_index(op.f("ix_feature_flag_changes_flag_key"), "feature_flag_changes", ["flag_key"], unique=False)
    op.create_index(op.f("ix_feature_flag_changes_created_at"), "feature_flag_changes", ["created_at"], unique=False)

    op.create_table(
        "promocodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promocodes")),
    )
    op.create_index(op.f("ix_promocodes_code"), "promocodes", ["code"], unique=True)
    op.create_index(op.f("ix_promocodes_is_active"), "promocodes", ["is_active"], unique=False)
    op.create_index(op.f("ix_promocodes_created_at"), "promocodes", ["created_at"], unique=False)

    op.create_table(
        "promocode_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("promocode_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_promocode_redemptions_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["promocode_id"], ["promocodes.id"], name=op.f("fk_promocode_redemptions_promocode_id_promocodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_promocode_redemptions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promocode_redemptions")),
    )
    op.create_index(op.f("ix_promocode_redemptions_promocode_id"), "promocode_redemptions", ["promocode_id"], unique=False)
    op.create_index(op.f("ix_promocode_redemptions_user_id"), "promocode_redemptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_promocode_redemptions_order_id"), "promocode_redemptions", ["order_id"], unique=False)
    op.create_index(op.f("ix_promocode_redemptions_created_at"), "promocode_redemptions", ["created_at"], unique=False)

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("tariff_code", sa.String(length=50), nullable=True),
        sa.Column("source_channel", sa.String(length=50), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("geo", sa.String(length=32), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("cost_components", sa.JSON(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_analytics_events_order_id_orders"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_analytics_events_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analytics_events")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_analytics_events_dedupe_key")),
    )
    op.create_index(op.f("ix_analytics_events_event_name"), "analytics_events", ["event_name"], unique=False)
    op.create_index(op.f("ix_analytics_events_user_id"), "analytics_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_analytics_events_order_id"), "analytics_events", ["order_id"], unique=False)
    op.create_index(op.f("ix_analytics_events_tariff_code"), "analytics_events", ["tariff_code"], unique=False)
    op.create_index(op.f("ix_analytics_events_source_channel"), "analytics_events", ["source_channel"], unique=False)
    op.create_index(op.f("ix_analytics_events_geo"), "analytics_events", ["geo"], unique=False)
    op.create_index(op.f("ix_analytics_events_platform"), "analytics_events", ["platform"], unique=False)
    op.create_index(op.f("ix_analytics_events_correlation_id"), "analytics_events", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_analytics_events_event_time"), "analytics_events", ["event_time"], unique=False)

    op.create_table(
        "marketing_spend_manual",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("campaign_name", sa.String(length=255), nullable=True),
        sa.Column("spend_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_marketing_spend_manual")),
    )
    op.create_index(op.f("ix_marketing_spend_manual_period_start"), "marketing_spend_manual", ["period_start"], unique=False)
    op.create_index(op.f("ix_marketing_spend_manual_period_end"), "marketing_spend_manual", ["period_end"], unique=False)
    op.create_index(op.f("ix_marketing_spend_manual_channel"), "marketing_spend_manual", ["channel"], unique=False)
    op.create_index(op.f("ix_marketing_spend_manual_campaign_name"), "marketing_spend_manual", ["campaign_name"], unique=False)
    op.create_index(op.f("ix_marketing_spend_manual_created_at"), "marketing_spend_manual", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_marketing_spend_manual_created_at"), table_name="marketing_spend_manual")
    op.drop_index(op.f("ix_marketing_spend_manual_campaign_name"), table_name="marketing_spend_manual")
    op.drop_index(op.f("ix_marketing_spend_manual_channel"), table_name="marketing_spend_manual")
    op.drop_index(op.f("ix_marketing_spend_manual_period_end"), table_name="marketing_spend_manual")
    op.drop_index(op.f("ix_marketing_spend_manual_period_start"), table_name="marketing_spend_manual")
    op.drop_table("marketing_spend_manual")

    op.drop_index(op.f("ix_analytics_events_event_time"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_correlation_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_platform"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_geo"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_source_channel"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_tariff_code"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_order_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_user_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_event_name"), table_name="analytics_events")
    op.drop_table("analytics_events")

    op.drop_index(op.f("ix_promocode_redemptions_created_at"), table_name="promocode_redemptions")
    op.drop_index(op.f("ix_promocode_redemptions_order_id"), table_name="promocode_redemptions")
    op.drop_index(op.f("ix_promocode_redemptions_user_id"), table_name="promocode_redemptions")
    op.drop_index(op.f("ix_promocode_redemptions_promocode_id"), table_name="promocode_redemptions")
    op.drop_table("promocode_redemptions")

    op.drop_index(op.f("ix_promocodes_created_at"), table_name="promocodes")
    op.drop_index(op.f("ix_promocodes_is_active"), table_name="promocodes")
    op.drop_index(op.f("ix_promocodes_code"), table_name="promocodes")
    op.drop_table("promocodes")

    op.drop_index(op.f("ix_feature_flag_changes_created_at"), table_name="feature_flag_changes")
    op.drop_index(op.f("ix_feature_flag_changes_flag_key"), table_name="feature_flag_changes")
    op.drop_table("feature_flag_changes")
    op.drop_table("feature_flags")

    op.drop_index(op.f("ix_admin_action_logs_created_at"), table_name="admin_action_logs")
    op.drop_index(op.f("ix_admin_action_logs_entity"), table_name="admin_action_logs")
    op.drop_index(op.f("ix_admin_action_logs_action"), table_name="admin_action_logs")
    op.drop_index(op.f("ix_admin_action_logs_actor_email"), table_name="admin_action_logs")
    op.drop_table("admin_action_logs")

    op.drop_index(op.f("ix_orders_promo_code"), table_name="orders")
    op.drop_column("orders", "infra_cost_amount")
    op.drop_column("orders", "ai_cost_amount")
    op.drop_column("orders", "payment_fee_amount")
    op.drop_column("orders", "variable_cost_amount")
    op.drop_column("orders", "payment_provider")
    op.drop_column("orders", "promo_code")

    op.drop_index(op.f("ix_users_signup_geo"), table_name="users")
    op.drop_index(op.f("ix_users_signup_platform"), table_name="users")
    op.drop_index(op.f("ix_users_source_channel"), table_name="users")
    op.drop_index(op.f("ix_users_utm_source"), table_name="users")
    op.drop_column("users", "acquisition_at")
    op.drop_column("users", "signup_geo")
    op.drop_column("users", "signup_platform")
    op.drop_column("users", "source_channel")
    op.drop_column("users", "utm_campaign")
    op.drop_column("users", "utm_medium")
    op.drop_column("users", "utm_source")
