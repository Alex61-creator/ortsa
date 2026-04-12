from pydantic import BaseModel, Field


class GeocodeResponse(BaseModel):
    lat: float
    lon: float
    timezone: str = Field(description="IANA timezone, e.g. Europe/Moscow")
    display_name: str
