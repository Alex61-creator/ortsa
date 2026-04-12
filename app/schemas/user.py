from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime
    consent_given_at: Optional[datetime] = None
    oauth_provider: Optional[str] = Field(
        default=None,
        description="Провайдер OAuth/Telegram, если аккаунт привязан",
    )

    class Config:
        from_attributes = True


class UserConsentPatch(BaseModel):
    """Согласие на обработку ПДн (без создания натальных данных)."""

    accept_privacy_policy: bool = True