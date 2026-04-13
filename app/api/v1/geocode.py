import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from timezonefinder import TimezoneFinder

from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.geocode import GeocodeResponse

router = APIRouter()
_tz_finder = TimezoneFinder()


@router.get(
    "/",
    response_model=GeocodeResponse,
    summary="Геокодинг места рождения",
    description="Поиск координат через Nominatim (OSM) и IANA timezone по точке (timezonefinder). Без авторизации.",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def geocode_lookup(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200, description="Город, страна"),
):
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 1},
            headers=headers,
            timeout=20.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Geocoding service error")
    data = resp.json()
    if not data:
        raise HTTPException(status_code=404, detail="Place not found")
    row = data[0]
    lat = float(row["lat"])
    lon = float(row["lon"])
    tz = _tz_finder.timezone_at(lng=lon, lat=lat) or "UTC"
    display = row.get("display_name") or q
    return GeocodeResponse(lat=lat, lon=lon, timezone=tz, display_name=display)
