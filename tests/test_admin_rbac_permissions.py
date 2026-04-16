from datetime import datetime

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import OAuthProvider, User
from app.api.deps import require_admin_permission
from fastapi import HTTPException


def _token_for_user(user: User) -> str:
    return create_access_token({"sub": str(user.id), "tv": user.token_version})


@pytest.mark.asyncio
async def test_admin_rbac_refund_requires_can_refund(
    client: AsyncClient,
    db_session,
):
    deny_admin = User(
        email="rbac-refund-deny@example.com",
        external_id="rbac-refund-deny",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_refund=False,
    )
    db_session.add(deny_admin)
    await db_session.commit()
    await db_session.refresh(deny_admin)

    headers = {"Authorization": f"Bearer {_token_for_user(deny_admin)}"}
    resp = await client.post("/api/v1/admin/orders/999999/refund", headers=headers, json={})
    assert resp.status_code == 403

    allow_admin = User(
        email="rbac-refund-allow@example.com",
        external_id="rbac-refund-allow",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_refund=True,
    )
    db_session.add(allow_admin)
    await db_session.commit()
    await db_session.refresh(allow_admin)

    headers_allow = {"Authorization": f"Bearer {_token_for_user(allow_admin)}"}
    resp2 = await client.post("/api/v1/admin/orders/999999/refund", headers=headers_allow, json={})
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_admin_rbac_retry_report_requires_can_retry_report(
    client: AsyncClient,
    db_session,
):
    deny_admin = User(
        email="rbac-retry-deny@example.com",
        external_id="rbac-retry-deny",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_retry_report=False,
    )
    db_session.add(deny_admin)
    await db_session.commit()
    await db_session.refresh(deny_admin)
    headers = {"Authorization": f"Bearer {_token_for_user(deny_admin)}"}

    resp = await client.post("/api/v1/admin/orders/999999/retry-report", headers=headers)
    assert resp.status_code == 403

    allow_admin = User(
        email="rbac-retry-allow@example.com",
        external_id="rbac-retry-allow",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_retry_report=True,
    )
    db_session.add(allow_admin)
    await db_session.commit()
    await db_session.refresh(allow_admin)
    headers_allow = {"Authorization": f"Bearer {_token_for_user(allow_admin)}"}

    resp2 = await client.post("/api/v1/admin/orders/999999/retry-report", headers=headers_allow)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_admin_rbac_resend_report_email_requires_can_resend_report_email(
    client: AsyncClient,
    db_session,
):
    deny_admin = User(
        email="rbac-resend-deny@example.com",
        external_id="rbac-resend-deny",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_resend_report_email=False,
    )
    db_session.add(deny_admin)
    await db_session.commit()
    await db_session.refresh(deny_admin)
    assert deny_admin.can_resend_report_email in (False, 0)
    with pytest.raises(HTTPException):
        await require_admin_permission("can_resend_report_email", current_user=deny_admin, db=db_session)
    headers = {"Authorization": f"Bearer {_token_for_user(deny_admin)}"}

    resp = await client.post("/api/v1/admin/orders/999999/resend-email", headers=headers, json={})
    assert resp.status_code in (403, 404)

    allow_admin = User(
        email="rbac-resend-allow@example.com",
        external_id="rbac-resend-allow",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_resend_report_email=True,
    )
    db_session.add(allow_admin)
    await db_session.commit()
    await db_session.refresh(allow_admin)
    assert allow_admin.can_resend_report_email in (True, 1)
    headers_allow = {"Authorization": f"Bearer {_token_for_user(allow_admin)}"}

    resp2 = await client.post("/api/v1/admin/orders/999999/resend-email", headers=headers_allow, json={})
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_admin_rbac_patch_synastry_override_requires_can_manual_override(
    client: AsyncClient,
    db_session,
):
    deny_admin = User(
        email="rbac-override-deny@example.com",
        external_id="rbac-override-deny",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_manual_override=False,
    )
    db_session.add(deny_admin)
    await db_session.commit()
    await db_session.refresh(deny_admin)
    headers = {"Authorization": f"Bearer {_token_for_user(deny_admin)}"}

    resp = await client.patch("/api/v1/admin/users/999999/synastry/override", headers=headers, json={})
    assert resp.status_code == 403

    allow_admin = User(
        email="rbac-override-allow@example.com",
        external_id="rbac-override-allow",
        oauth_provider=OAuthProvider.GOOGLE,
        consent_given_at=datetime.utcnow(),
        is_admin=True,
        can_manual_override=True,
    )
    db_session.add(allow_admin)
    await db_session.commit()
    await db_session.refresh(allow_admin)
    headers_allow = {"Authorization": f"Bearer {_token_for_user(allow_admin)}"}

    resp2 = await client.patch("/api/v1/admin/users/999999/synastry/override", headers=headers_allow, json={})
    assert resp2.status_code == 404

