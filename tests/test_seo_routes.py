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
    assert "/order/tariff" in r.text
    assert "urlset" in r.text


@pytest.mark.asyncio
async def test_root_redirects_to_react_tariff():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307, 308)
    assert r.headers.get("location") == "/order/tariff"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "location"),
    [
        ("/privacy", "/order/tariff"),
        ("/oferta", "/order/tariff"),
        ("/sample-report.html", "/order/tariff"),
        ("/auth/callback", "/order/tariff"),
        ("/cabinet", "/dashboard"),
    ],
)
async def test_legacy_public_routes_redirect_to_react(path: str, location: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(path, follow_redirects=False)
    assert r.status_code in (302, 307, 308)
    assert r.headers.get("location") == location
