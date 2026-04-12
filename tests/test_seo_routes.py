import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_robots_txt_contains_sitemap():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap:" in r.text
    assert "Disallow: /api/" in r.text
    assert "http://test/sitemap.xml" in r.text


@pytest.mark.asyncio
async def test_sitemap_xml_urls():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "http://test/" in r.text or "http://test</loc>" in r.text.replace("\n", "")
    assert "/privacy" in r.text
    assert "urlset" in r.text


@pytest.mark.asyncio
async def test_landing_replaces_site_placeholder():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
    assert r.status_code == 200
    assert "__SITE_BASE_URL__" not in r.text
    assert "http://test" in r.text
    assert 'rel="canonical"' in r.text
