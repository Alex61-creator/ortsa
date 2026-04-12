from zoneinfo import ZoneInfo, available_timezones
from datetime import datetime

def validate_timezone(tz_str: str) -> bool:
    return tz_str in available_timezones()

def localize_datetime(dt: datetime, tz_str: str) -> datetime:
    return dt.replace(tzinfo=ZoneInfo(tz_str))