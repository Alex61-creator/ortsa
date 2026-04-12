from app.constants.tariffs import FEATURE_KEY_MAX_NATAL_PROFILES
from app.models.tariff import Tariff


def max_natal_profiles_from_tariff(tariff: Tariff) -> int:
    raw = (tariff.features or {}).get(FEATURE_KEY_MAX_NATAL_PROFILES, 1)
    try:
        n = int(raw)
        return max(1, n)
    except (TypeError, ValueError):
        return 1
