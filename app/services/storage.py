import asyncio
import aiofiles
from pathlib import Path
import structlog
from datetime import datetime, timezone

from app.core.config import settings

logger = structlog.get_logger(__name__)

class StorageService:
    def __init__(self, base_dir: Path = settings.STORAGE_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_data: bytes, relative_path: str) -> Path:
        full_path = self.base_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_data)
        return full_path

    def resolve_path(self, raw_path: str | Path | None) -> Path | None:
        if not raw_path:
            return None
        p = Path(raw_path)
        if p.is_absolute():
            return p
        return self.base_dir / p

    def to_storage_key(self, full_path: str | Path) -> str:
        p = Path(full_path)
        if p.is_absolute():
            try:
                return str(p.relative_to(self.base_dir))
            except ValueError:
                return str(p)
        try:
            return str(p.relative_to(self.base_dir))
        except ValueError:
            pass
        return str(p)

    async def read_file(self, relative_path: str) -> bytes | None:
        full_path = self.base_dir / relative_path
        if not full_path.exists():
            return None
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete_file(self, relative_path: str) -> bool:
        full_path = self.base_dir / relative_path
        try:
            await asyncio.to_thread(full_path.unlink, missing_ok=True)
            return True
        except Exception as e:
            logger.error("Failed to delete file", path=str(full_path), error=str(e))
            return False

    async def cleanup_old_files(self, retention_days: int) -> int:
        import time
        cutoff = time.time() - retention_days * 86400
        deleted = 0
        # Ограничиваем сканирование только каталогами с артефактами отчётов.
        # Полный **/* на большом storage становится заметно дороже.
        roots = (self.base_dir / "reports", self.base_dir / "charts")
        for root in roots:
            if not root.exists():
                continue
            for file_path in root.glob("**/*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        if stat.st_mtime < cutoff:
                            await self.delete_file(str(file_path.relative_to(self.base_dir)))
                            deleted += 1
                    except Exception as e:
                        logger.error("Cleanup error", path=str(file_path), error=str(e))
        return deleted

    async def delete_if_expired(self, raw_path: str | Path | None, expires_at: datetime | None) -> bool:
        if not raw_path or not expires_at:
            return False
        now = datetime.now(timezone.utc)
        exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if exp > now:
            return False
        full_path = self.resolve_path(raw_path)
        if not full_path:
            return False
        rel = self.to_storage_key(full_path)
        return await self.delete_file(rel)