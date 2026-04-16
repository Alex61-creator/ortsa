from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.cache import cache
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_extra import UserNoteCreate, UserNoteOut
from app.services.admin_logs import append_admin_log

router = APIRouter()


class UserEmailPatch(BaseModel):
    email: EmailStr


class UserBlockState(BaseModel):
    user_id: int
    blocked: bool


async def _require_user(db: AsyncSession, user_id: int) -> User:
    row = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return row


@router.patch("/users/{user_id}/email", summary="Support: смена email")
async def patch_user_email(
    user_id: int,
    payload: UserEmailPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = await _require_user(db, user_id)
    user.email = str(payload.email).lower()
    await db.commit()
    await append_admin_log(db, _.email or f"user:{_.id}", "user_email_patch", f"user:{user_id}")
    return {"user_id": user.id, "email": user.email}


@router.post("/users/{user_id}/block", response_model=UserBlockState, summary="Support: блокировка")
async def block_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    await _require_user(db, user_id)
    await cache.set(f"admin:block:{user_id}", True)
    await append_admin_log(db, _.email or f"user:{_.id}", "user_block", f"user:{user_id}")
    return UserBlockState(user_id=user_id, blocked=True)


@router.post("/users/{user_id}/unblock", response_model=UserBlockState, summary="Support: разблокировка")
async def unblock_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    await _require_user(db, user_id)
    await cache.set(f"admin:block:{user_id}", False)
    await append_admin_log(db, _.email or f"user:{_.id}", "user_unblock", f"user:{user_id}")
    return UserBlockState(user_id=user_id, blocked=False)


@router.get("/users/{user_id}/notes", response_model=list[UserNoteOut], summary="Support: заметки")
async def list_notes(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    await _require_user(db, user_id)
    data = await cache.get(f"admin:notes:{user_id}")
    if not isinstance(data, list):
        return []
    return [UserNoteOut(**x) for x in data]


@router.post("/users/{user_id}/notes", response_model=UserNoteOut, summary="Support: добавить заметку")
async def add_note(
    user_id: int,
    payload: UserNoteCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    await _require_user(db, user_id)
    key = f"admin:notes:{user_id}"
    data = await cache.get(key)
    notes = data if isinstance(data, list) else []
    row = UserNoteOut(id=str(uuid4()), text=payload.text, created_at=datetime.utcnow()).model_dump(mode="json")
    notes.append(row)
    await cache.set(key, notes)
    await append_admin_log(db, _.email or f"user:{_.id}", "user_note_add", f"user:{user_id}")
    return UserNoteOut(**row)
