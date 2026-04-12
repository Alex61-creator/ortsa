import pytest
from decimal import Decimal
from app.services.tariff import TariffService
from app.models.tariff import Tariff

@pytest.mark.asyncio
async def test_tariff_cache(db_session):
    tariff = Tariff(
        code="test",
        name="Test",
        price=100,
        price_usd=Decimal("1.05"),
        features={"max_natal_profiles": 1},
        retention_days=30,
        llm_tier="natal_full",
    )
    db_session.add(tariff)
    await db_session.commit()
    t1 = await TariffService.get_by_code(db_session, "test")
    t2 = await TariffService.get_by_code(db_session, "test")
    assert t1.code == t2.code