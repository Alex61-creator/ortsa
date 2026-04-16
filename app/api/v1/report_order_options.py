"""Публичные опции доп. разделов отчёта (report / bundle) для визарда."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.report_options import report_option_definitions
from app.core.feature_flags import FeatureFlags
from app.db.session import get_db
from app.services.report_option_pricing import load_report_option_price_map_and_multi

router = APIRouter()

REPORT_UPSELL_FLAG = "report_upsell_sections_enabled"


class ReportOrderOptionItem(BaseModel):
    key: str
    title: str
    description: str
    price: str = Field(description="Цена в RUB как строка для UI")
    currency: str = "RUB"


class ReportOrderOptionsOut(BaseModel):
    feature_enabled: bool
    options: list[ReportOrderOptionItem]
    multi_discount_percent: int = Field(ge=0, le=100)
    currency: str = "RUB"


@router.get(
    "/",
    response_model=ReportOrderOptionsOut,
    summary="Опции доп. разделов отчёта (report/bundle)",
    description="Цены из app_settings; при выключенном флаге report_upsell_sections_enabled — пустой список.",
)
async def get_report_order_options(db: AsyncSession = Depends(get_db)) -> ReportOrderOptionsOut:
    enabled = await FeatureFlags.is_enabled(REPORT_UPSELL_FLAG, default=False)
    if not enabled:
        return ReportOrderOptionsOut(
            feature_enabled=False,
            options=[],
            multi_discount_percent=0,
        )

    price_by_key, multi = await load_report_option_price_map_and_multi(db)
    defs = report_option_definitions()
    options: list[ReportOrderOptionItem] = []
    for d in defs:
        p = price_by_key.get(d.key, Decimal("0"))
        options.append(
            ReportOrderOptionItem(
                key=d.key,
                title=d.title,
                description=d.description,
                price=str(p.quantize(Decimal("0.01"))),
            )
        )
    return ReportOrderOptionsOut(
        feature_enabled=True,
        options=options,
        multi_discount_percent=int(multi),
    )
