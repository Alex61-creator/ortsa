import asyncio
from datetime import datetime

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            email=settings.ADMIN_EMAIL,
            is_admin=True,
            consent_given_at=datetime.utcnow()
        )
        db.add(user)
        await db.commit()
        print(f"Admin user {settings.ADMIN_EMAIL} created")

if __name__ == "__main__":
    asyncio.run(create_admin())