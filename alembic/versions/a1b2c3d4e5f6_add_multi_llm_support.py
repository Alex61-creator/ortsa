"""add multi-llm support

Revision ID: a1b2c3d4e5f6
Revises: z9y8x7w6v5u4
Create Date: 2026-04-26

Изменения:
- llm_usage_logs: создать таблицу (provider, cached_tokens)
- reports: добавить llm_provider
- synastry_reports: добавить llm_provider
- llm_prompt_templates: добавить llm_provider, заменить UniqueConstraint
- app_settings: seed-записи для управления провайдерами
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── llm_usage_logs (создаём если не существует) ───────────────────────────
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "llm_usage_logs" not in existing_tables:
        op.create_table(
            "llm_usage_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("provider", sa.String(20), nullable=False, server_default="deepseek"),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), nullable=False),
            sa.Column("total_tokens", sa.Integer(), nullable=False),
            sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
            sa.Column("cost_rub", sa.Numeric(12, 4), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_llm_usage_logs_user_id", "llm_usage_logs", ["user_id"])
        op.create_index("ix_llm_usage_logs_order_id", "llm_usage_logs", ["order_id"])
        op.create_index("ix_llm_usage_logs_provider", "llm_usage_logs", ["provider"])
    else:
        # Таблица уже есть — добавляем только новые колонки
        existing_cols = {c["name"] for c in inspector.get_columns("llm_usage_logs")}
        if "provider" not in existing_cols:
            op.add_column("llm_usage_logs", sa.Column("provider", sa.String(20), nullable=False, server_default="deepseek"))
            op.create_index("ix_llm_usage_logs_provider", "llm_usage_logs", ["provider"])
        if "cached_tokens" not in existing_cols:
            op.add_column("llm_usage_logs", sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"))

    # ── reports ───────────────────────────────────────────────────────────────
    rep_cols = {c["name"] for c in inspector.get_columns("reports")}
    if "llm_provider" not in rep_cols:
        op.add_column("reports", sa.Column("llm_provider", sa.String(20), nullable=True))
        op.create_index("ix_reports_llm_provider", "reports", ["llm_provider"])

    # ── synastry_reports ──────────────────────────────────────────────────────
    syn_cols = {c["name"] for c in inspector.get_columns("synastry_reports")}
    if "llm_provider" not in syn_cols:
        op.add_column("synastry_reports", sa.Column("llm_provider", sa.String(20), nullable=True))

    # ── llm_prompt_templates ──────────────────────────────────────────────────
    tpl_cols = {c["name"] for c in inspector.get_columns("llm_prompt_templates")}
    if "llm_provider" not in tpl_cols:
        op.add_column("llm_prompt_templates", sa.Column("llm_provider", sa.String(20), nullable=True))

    # Заменяем уникальный ключ (old: tariff_code+locale, new: +llm_provider)
    existing_constraints = {c["name"] for c in inspector.get_unique_constraints("llm_prompt_templates")}
    if "uq_llm_prompt_code_locale" in existing_constraints:
        op.drop_constraint("uq_llm_prompt_code_locale", "llm_prompt_templates", type_="unique")
    if "uq_llm_prompt_code_locale_provider" not in existing_constraints:
        op.create_unique_constraint(
            "uq_llm_prompt_code_locale_provider",
            "llm_prompt_templates",
            ["tariff_code", "locale", "llm_provider"],
        )

    # ── app_settings: seed LLM provider config ────────────────────────────────
    op.execute("""
        INSERT INTO app_settings (key, value, description, updated_at)
        VALUES
            ('llm_primary_provider',          'claude',               'Основной LLM-провайдер: deepseek | grok | claude', NOW()),
            ('llm_fallback_order',            'claude,grok,deepseek', 'Порядок fallback через запятую', NOW()),
            ('llm_provider_claude_enabled',   'true',                 'Claude Sonnet 4.6 включён', NOW()),
            ('llm_provider_grok_enabled',     'false',                'Grok 4.20 включён', NOW()),
            ('llm_provider_deepseek_enabled', 'true',                 'DeepSeek включён (последний fallback)', NOW())
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM app_settings WHERE key IN (
            'llm_primary_provider','llm_fallback_order',
            'llm_provider_claude_enabled','llm_provider_grok_enabled',
            'llm_provider_deepseek_enabled'
        )
    """)
    op.drop_constraint("uq_llm_prompt_code_locale_provider", "llm_prompt_templates", type_="unique")
    op.drop_column("llm_prompt_templates", "llm_provider")
    op.create_unique_constraint("uq_llm_prompt_code_locale", "llm_prompt_templates", ["tariff_code", "locale"])
    op.drop_index("ix_reports_llm_provider", "reports")
    op.drop_column("reports", "llm_provider")
    op.drop_column("synastry_reports", "llm_provider")
    op.drop_index("ix_llm_usage_logs_provider", "llm_usage_logs")
    op.drop_column("llm_usage_logs", "cached_tokens")
    op.drop_column("llm_usage_logs", "provider")
