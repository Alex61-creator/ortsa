from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    id: int
    email: str
    oauth_provider: str
    is_admin: bool
    created_at: datetime
    consent_given_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserOut(BaseModel):
    id: int
    email: str
    oauth_provider: str
    external_id: str
    is_admin: bool
    created_at: datetime
    consent_given_at: Optional[datetime] = None

    class Config:
        from_attributes = True
