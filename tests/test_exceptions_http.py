import logging

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_http_4xx_logged_as_warning(caplog, client: AsyncClient, auth_headers):
    with caplog.at_level(logging.WARNING):
        await client.get("/api/v1/orders/99999", headers=auth_headers)
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)
