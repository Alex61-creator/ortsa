from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal, Optional
from zoneinfo import available_timezones

class NatalDataBase(BaseModel):
    full_name: str = Field(..., max_length=80)
    birth_date: datetime
    birth_time: datetime
    birth_place: str = Field(..., max_length=120)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    timezone: str
    house_system: str = "P"
    report_locale: Literal["ru", "en"] = Field(
        default="ru",
        description="Язык отчёта (PDF и письма): ru или en.",
    )

    @field_validator("timezone")
    def validate_timezone(cls, v):
        if v not in available_timezones():
            raise ValueError("Invalid timezone")
        return v

class NatalDataCreate(NatalDataBase):
    accept_privacy_policy: bool = Field(
        default=False,
        description="Согласие с политикой; обязательно при первом сохранении, если согласие ещё не зафиксировано в профиле.",
    )

class NatalDataUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=80)
    birth_place: Optional[str] = Field(None, max_length=120)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    timezone: Optional[str] = None
    house_system: Optional[str] = None
    report_locale: Optional[Literal["ru", "en"]] = None

class NatalDataOut(NatalDataBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True