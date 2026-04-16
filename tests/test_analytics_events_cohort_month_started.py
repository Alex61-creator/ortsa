import pytest
from sqlalchemy import select

from app.api.v1.auth import oauth_callback
from app.models.analytics_event import AnalyticsEvent
from app.models.user import OAuthProvider, User


async def _get_user_by_external_id(db_session, external_id: str, provider: OAuthProvider) -> User:
    res = await db_session.execute(
        select(User).where(User.external_id == external_id, User.oauth_provider == provider)
    )
    return res.scalar_one()


async def _count_events(db_session, event_name: str) -> int:
    res = await db_session.execute(select(AnalyticsEvent.id).where(AnalyticsEvent.event_name == event_name))
    return len(res.scalars().all())


async def _get_event_rows(db_session, event_name: str, user_id: int) -> list[AnalyticsEvent]:
    res = await db_session.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.event_name == event_name, AnalyticsEvent.user_id == user_id)
    )
    return res.scalars().all()


async def _get_event_time(db_session, event_name: str, user_id: int):
    rows = await _get_event_rows(db_session, event_name, user_id=user_id)
    assert len(rows) == 1
    return rows[0].event_time


async def _invoke_oauth_callback(db_session, external_id: str, email: str):
    await oauth_callback(
        {"id": external_id, "email": email},
        OAuthProvider.GOOGLE,
        db_session,
    )


@pytest.mark.asyncio
async def test_cohort_month_started_emitted_once(db_session):
    external_id = "go_cohort_1"
    await _invoke_oauth_callback(db_session, external_id, "cohort1@example.com")

    user = await _get_user_by_external_id(db_session, external_id, OAuthProvider.GOOGLE)
    assert await _count_events(db_session, "cohort_month_started") == 1

    signup_time = await _get_event_time(db_session, "signup_completed", user_id=user.id)
    cohort_time = await _get_event_time(db_session, "cohort_month_started", user_id=user.id)
    assert cohort_time == signup_time

    # Second callback: user exists => cohort anchor must not be re-emitted.
    await _invoke_oauth_callback(db_session, external_id, "cohort1_new@example.com")
    assert await _count_events(db_session, "cohort_month_started") == 1

