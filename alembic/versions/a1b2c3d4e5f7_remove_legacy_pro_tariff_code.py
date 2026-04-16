"""remove legacy tariff code pro (merge FKs, clean JSON, prompts)

Revision ID: a1b2c3d4e5f7
Revises: z9y8x7w6v5u4
Create Date: 2026-04-16

- Переносит orders/subscriptions с tariffs.id(code=pro) на sub_monthly, удаляет строку pro;
  если sub_monthly нет — переименовывает pro → sub_monthly.
- Удаляет \"pro\" из addon_requires_tariff_codes в features.
- llm_prompt_templates: дубликаты по locale удаляются, остальное pro → sub_monthly.

llm_tier = 'pro' у подписок не трогаем — это уровень LLM, не код тарифа.
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DO $body$
            DECLARE
              pro_id integer;
              sm_id integer;
            BEGIN
              SELECT id INTO pro_id FROM tariffs WHERE code = 'pro' LIMIT 1;
              SELECT id INTO sm_id FROM tariffs WHERE code = 'sub_monthly' LIMIT 1;

              IF pro_id IS NOT NULL AND sm_id IS NOT NULL THEN
                UPDATE orders SET tariff_id = sm_id WHERE tariff_id = pro_id;
                UPDATE subscriptions SET tariff_id = sm_id WHERE tariff_id = pro_id;
                DELETE FROM tariffs WHERE id = pro_id;
              ELSIF pro_id IS NOT NULL AND sm_id IS NULL THEN
                UPDATE tariffs SET code = 'sub_monthly' WHERE id = pro_id;
              END IF;
            END
            $body$;
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE tariffs t
            SET features = (
                jsonb_set(
                    t.features::jsonb,
                    '{addon_requires_tariff_codes}',
                    COALESCE(
                        (
                            SELECT jsonb_agg(elem)
                            FROM jsonb_array_elements(t.features::jsonb->'addon_requires_tariff_codes') AS elem
                            WHERE elem #>> '{}' IS DISTINCT FROM 'pro'
                        ),
                        '[]'::jsonb
                    )
                )
            )::json
            WHERE jsonb_typeof(t.features::jsonb->'addon_requires_tariff_codes') = 'array'
              AND EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements(t.features::jsonb->'addon_requires_tariff_codes') AS e
                  WHERE e #>> '{}' = 'pro'
              );
            """
        )
    )

    conn.execute(
        sa.text(
            """
            DO $body$
            BEGIN
              IF EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema = 'public' AND table_name = 'llm_prompt_templates'
              ) THEN
                DELETE FROM llm_prompt_templates t
                WHERE t.tariff_code = 'pro'
                  AND EXISTS (
                      SELECT 1 FROM llm_prompt_templates s
                      WHERE s.tariff_code = 'sub_monthly' AND s.locale = t.locale
                  );

                UPDATE llm_prompt_templates
                SET tariff_code = 'sub_monthly'
                WHERE tariff_code = 'pro';
              END IF;
            END
            $body$;
            """
        )
    )


def downgrade() -> None:
    # Не восстанавливаем удалённый тариф pro и переназначения FK без снимка данных.
    pass
