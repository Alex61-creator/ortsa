from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.analytics_event import AnalyticsEvent
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import OAuthProvider, User
from app.services.event_based_metrics import (
    compute_funnel_steps,
    compute_growth_metrics,
    compute_retention_cohorts,
)


def _dt_utc(s: str) -> datetime:
    # s example: "2026-01-05T12:00:00Z"
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_event_based_metrics_services_funnel_growth_and_retention(db_session):
    # Users
    user1 = User(
        email="u1@example.com",
        external_id="u1",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="tg_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    user2 = User(
        email="u2@example.com",
        external_id="u2",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="tg_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    user3 = User(
        email="u3@example.com",
        external_id="u3",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        source_channel="email_ads",
        signup_platform="web",
        signup_geo="RU",
    )
    db_session.add_all([user1, user2, user3])

    # Tariffs
    bundle = Tariff(
        code="bundle",
        name="Bundle",
        price=Decimal("100.00"),
        price_usd=Decimal("1.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    synastry = Tariff(
        code="synastry_addon",
        name="Synastry Addon",
        price=Decimal("20.00"),
        price_usd=Decimal("0.20"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    report = Tariff(
        code="report",
        name="Report",
        price=Decimal("300.00"),
        price_usd=Decimal("3.00"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add_all([bundle, synastry, report])
    await db_session.commit()
    await db_session.flush()

    # Orders for FK integrity + stable order_ids for event rows.
    order1 = Order(
        user_id=user1.id,
        tariff_id=bundle.id,
        amount=Decimal("100.00"),
        status=OrderStatus.COMPLETED,
    )
    order2 = Order(
        user_id=user2.id,
        tariff_id=bundle.id,
        amount=Decimal("200.00"),
        status=OrderStatus.COMPLETED,
    )
    addon_order = Order(
        user_id=user1.id,
        tariff_id=synastry.id,
        amount=Decimal("20.00"),
        status=OrderStatus.COMPLETED,
    )

    # Retention month orders for user1 only.
    order_feb = Order(
        user_id=user1.id,
        tariff_id=bundle.id,
        amount=Decimal("120.00"),
        status=OrderStatus.COMPLETED,
    )
    order_apr = Order(
        user_id=user1.id,
        tariff_id=bundle.id,
        amount=Decimal("130.00"),
        status=OrderStatus.COMPLETED,
    )
    order_jul = Order(
        user_id=user1.id,
        tariff_id=bundle.id,
        amount=Decimal("140.00"),
        status=OrderStatus.COMPLETED,
    )

    order3_report = Order(
        user_id=user3.id,
        tariff_id=report.id,
        amount=Decimal("300.00"),
        status=OrderStatus.COMPLETED,
    )

    db_session.add_all([order1, order2, addon_order, order_feb, order_apr, order_jul, order3_report])
    await db_session.commit()
    await db_session.flush()

    start_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 2, 1, tzinfo=timezone.utc)

    # Seed analytics events with fixed event_time for determinism.
    events: list[AnalyticsEvent] = []

    # Signup + first paid + cohort anchor (tg_ads)
    events.append(
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user1.id,
            tariff_code=None,
            order_id=None,
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:user1:jan",
            event_time=_dt_utc("2026-01-05T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user2.id,
            tariff_code=None,
            order_id=None,
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:user2:jan",
            event_time=_dt_utc("2026-01-10T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user1.id,
            order_id=order1.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=order1.amount,
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fpc:user1:jan",
            event_time=_dt_utc("2026-01-06T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user2.id,
            order_id=order2.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=order2.amount,
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fpc:user2:jan",
            event_time=_dt_utc("2026-01-11T12:00:00Z"),
        )
    )

    events.append(
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=user1.id,
            order_id=None,
            tariff_code=None,
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"cohort:user1:jan",
            event_time=_dt_utc("2026-01-05T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=user2.id,
            order_id=None,
            tariff_code=None,
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"cohort:user2:jan",
            event_time=_dt_utc("2026-01-10T12:00:00Z"),
        )
    )

    # Order completed (tg_ads, bundle) within period.
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user1.id,
            order_id=order1.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("100.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 1.0,
                "payment_fee_amount": 2.0,
                "ai_cost_amount": 3.0,
                "infra_cost_amount": 4.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order1.id}",
            event_time=_dt_utc("2026-01-20T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user2.id,
            order_id=order2.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("200.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 2.0,
                "payment_fee_amount": 3.0,
                "ai_cost_amount": 1.0,
                "infra_cost_amount": 4.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order2.id}",
            event_time=_dt_utc("2026-01-25T12:00:00Z"),
        )
    )

    # Addon attached within period (synastry_addon).
    events.append(
        AnalyticsEvent(
            event_name="addon_attached",
            user_id=user1.id,
            order_id=addon_order.id,
            tariff_code="synastry_addon",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("20.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"aa:{addon_order.id}",
            event_time=_dt_utc("2026-01-21T12:00:00Z"),
        )
    )

    # Refund within period.
    events.append(
        AnalyticsEvent(
            event_name="refund_completed",
            user_id=user1.id,
            order_id=order1.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("50.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="refund:user1:jan",
            event_time=_dt_utc("2026-01-28T12:00:00Z"),
        )
    )

    # Acquisition spend.
    events.append(
        AnalyticsEvent(
            event_name="acquisition_cost_recorded",
            user_id=None,
            order_id=None,
            tariff_code=None,
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="spend:tg_ads:jan",
            event_time=_dt_utc("2026-01-15T12:00:00Z"),
        )
    )

    # Retention orders (M1/M3/M6 for user1 only)
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user1.id,
            order_id=order_feb.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("120.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order_feb.id}",
            event_time=_dt_utc("2026-02-05T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user1.id,
            order_id=order_apr.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("130.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order_apr.id}",
            event_time=_dt_utc("2026-04-05T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user1.id,
            order_id=order_jul.id,
            tariff_code="bundle",
            source_channel="tg_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("140.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order_jul.id}",
            event_time=_dt_utc("2026-07-05T12:00:00Z"),
        )
    )

    # User3 events (different segment): should be excluded by filters.
    events.append(
        AnalyticsEvent(
            event_name="signup_completed",
            user_id=user3.id,
            order_id=None,
            tariff_code=None,
            source_channel="email_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="signup:user3:jan",
            event_time=_dt_utc("2026-01-07T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="first_purchase_completed",
            user_id=user3.id,
            order_id=order3_report.id,
            tariff_code="report",
            source_channel="email_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="fpc:user3:jan",
            event_time=_dt_utc("2026-01-08T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="cohort_month_started",
            user_id=user3.id,
            order_id=None,
            tariff_code=None,
            source_channel="email_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=None,
            currency=None,
            cost_components=None,
            event_metadata=None,
            correlation_id=None,
            dedupe_key="cohort:user3:jan",
            event_time=_dt_utc("2026-01-07T12:00:00Z"),
        )
    )
    events.append(
        AnalyticsEvent(
            event_name="order_completed",
            user_id=user3.id,
            order_id=order3_report.id,
            tariff_code="report",
            source_channel="email_ads",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            geo=None,
            platform=None,
            amount=Decimal("300.00"),
            currency="RUB",
            cost_components={
                "variable_cost_amount": 1.0,
                "payment_fee_amount": 1.0,
                "ai_cost_amount": 1.0,
                "infra_cost_amount": 1.0,
            },
            event_metadata=None,
            correlation_id=None,
            dedupe_key=f"oc:{order3_report.id}",
            event_time=_dt_utc("2026-01-12T12:00:00Z"),
        )
    )

    db_session.add_all(events)
    await db_session.commit()

    # Funnel + growth metrics with segmentation to base tariff and channel.
    funnel_steps = await compute_funnel_steps(
        db_session,
        start_at,
        end_at,
        tariff_code="bundle",
        source_channel="tg_ads",
    )
    step_map = {s.key: s for s in funnel_steps}
    assert step_map["signup"].count == 2
    assert step_map["first_purchase"].count == 2
    assert step_map["completed"].count == 2
    assert step_map["addon"].count == 1
    assert step_map["addon"].conversion_pct == 50.0

    growth = await compute_growth_metrics(
        db_session,
        start_at,
        end_at,
        tariff_code="bundle",
        source_channel="tg_ads",
    )
    assert growth["signups"] == 2
    assert growth["first_paid_users"] == 2
    assert growth["revenue"] == 300.0
    assert growth["paid_orders"] == 2
    assert growth["addon_orders"] == 1
    assert growth["eligible_orders"] == 2
    assert growth["refunded"] == 50.0
    assert growth["variable_costs"] == 20.0
    assert growth["attach_rate"] == 0.5
    assert growth["cr1"] == 1.0
    assert growth["aov"] == 150.0
    assert growth["spend"] == 300.0
    assert growth["blended_cac"] == 150.0
    assert growth["contribution_margin"] == pytest.approx(0.7666666666, rel=1e-5)

    cohorts = await compute_retention_cohorts(
        db_session,
        start_at,
        end_at,
        tariff_code="bundle",
        source_channel="tg_ads",
    )
    assert len(cohorts) == 1
    assert cohorts[0].cohort == "2026-01"
    assert cohorts[0].size == 2
    assert cohorts[0].m1 == 50.0
    assert cohorts[0].m3 == 50.0
    assert cohorts[0].m6 == 50.0

