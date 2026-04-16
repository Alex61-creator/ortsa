"""Серверные CSV-выгрузки для админ-аналитики."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User
from app.models.subscription import Subscription
from app.models.tariff import Tariff
from app.models.user import User
from app.services.event_based_metrics import compute_campaign_performance

router = APIRouter()


def _csv_stream(rows: list[list[str]], excel_bom: bool) -> AsyncIterator[bytes]:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    data = buf.getvalue()
    if excel_bom:
        data = "\ufeff" + data
    yield data.encode("utf-8")


@router.get("/orders.csv", summary="CSV заказов (срез по датам создания)")
async def export_orders_csv(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    billing_type: str | None = Query(
        default=None,
        description="Фильтр tariffs.billing_type: one_time | subscription",
    ),
    excel_bom: int = Query(default=0, ge=0, le=1),
    limit: int = Query(default=5000, ge=1, le=20000),
):
    now = datetime.now(timezone.utc)
    end_at = date_to or now
    start_at = date_from or (end_at - timedelta(days=365))
    stmt = select(Order).where(Order.created_at >= start_at, Order.created_at < end_at)
    if billing_type:
        stmt = stmt.join(Tariff, Tariff.id == Order.tariff_id).where(Tariff.billing_type == billing_type)
    stmt = stmt.options(joinedload(Order.tariff)).order_by(Order.created_at.desc()).limit(limit)
    orders = (await db.execute(stmt)).unique().scalars().all()
    header = [
        "id",
        "user_id",
        "status",
        "amount",
        "promo_code",
        "tariff_code",
        "billing_type",
        "report_option_flags_json",
        "created_at",
    ]
    lines: list[list[str]] = [header]
    for o in orders:
        flags = o.report_option_flags
        flags_s = "" if flags is None else json.dumps(flags, ensure_ascii=False)
        lines.append(
            [
                str(o.id),
                str(o.user_id),
                o.status.value if hasattr(o.status, "value") else str(o.status),
                str(o.amount),
                o.promo_code or "",
                o.tariff.code if o.tariff else "",
                o.tariff.billing_type if o.tariff else "",
                flags_s,
                o.created_at.isoformat() if o.created_at else "",
            ]
        )
    bom = bool(excel_bom)
    return StreamingResponse(
        _csv_stream(lines, bom),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders_export.csv"'},
    )


@router.get("/subscriptions.csv", summary="CSV подписок")
async def export_subscriptions_csv(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    excel_bom: int = Query(default=0, ge=0, le=1),
    limit: int = Query(default=5000, ge=1, le=20000),
):
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.created_at.desc())
        .limit(limit)
    )
    subs = (await db.execute(stmt)).unique().scalars().all()
    header = [
        "id",
        "user_id",
        "tariff_code",
        "status",
        "current_period_start",
        "current_period_end",
        "created_at",
    ]
    lines: list[list[str]] = [header]
    for s in subs:
        lines.append(
            [
                str(s.id),
                str(s.user_id),
                s.tariff.code if s.tariff else "",
                s.status,
                s.current_period_start.isoformat() if s.current_period_start else "",
                s.current_period_end.isoformat() if s.current_period_end else "",
                s.created_at.isoformat() if s.created_at else "",
            ]
        )
    return StreamingResponse(
        _csv_stream(lines, bool(excel_bom)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="subscriptions_export.csv"'},
    )


@router.get("/campaign-performance.csv", summary="CSV кампаний (как JSON-отчёт)")
async def export_campaign_csv(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    group_by: Literal["campaign", "source"] = Query(default="campaign"),
    billing_segment: Literal["all", "one_time", "subscription"] = Query(default="all"),
    excel_bom: int = Query(default=0, ge=0, le=1),
):
    now = datetime.now(timezone.utc)
    if date_from and date_to:
        start_at, end_at = date_from, date_to
        if end_at <= start_at:
            start_at, end_at = end_at - timedelta(days=30), end_at
    else:
        end_at = now
        start_at = end_at - timedelta(days=30)
    seg = None if billing_segment == "all" else billing_segment
    rows_raw, _ = await compute_campaign_performance(
        db, start_at, end_at, group_by=group_by, billing_segment=seg
    )
    header = [
        "segment_key",
        "signups",
        "first_paid_users",
        "first_paid_revenue_rub",
        "orders_completed",
        "cr1",
    ]
    lines: list[list[str]] = [header]
    for r in rows_raw:
        lines.append(
            [
                str(r["segment_key"]),
                str(r["signups"]),
                str(r["first_paid_users"]),
                str(r["first_paid_revenue_rub"]),
                str(r["orders_completed"]),
                str(r["cr1"]),
            ]
        )
    return StreamingResponse(
        _csv_stream(lines, bool(excel_bom)),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="campaign_performance.csv"'},
    )
