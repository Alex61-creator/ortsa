import asyncio
import aiofiles
from pathlib import Path
import structlog

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
        for file_path in self.base_dir.glob("**/*"):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    if stat.st_mtime < cutoff:
                        await self.delete_file(str(file_path.relative_to(self.base_dir)))
                        deleted += 1
                except Exception as e:
                    logger.error("Cleanup error", path=str(file_path), error=str(e))
        return deleted