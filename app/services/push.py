import structlog

logger = structlog.get_logger(__name__)


class PushService:
    async def send_push(self, *, user_id: int, title: str, body: str, deep_link: str) -> None:
        # Thin abstraction: currently logs dispatch intent.
        logger.info(
            "Push notification sent",
            user_id=user_id,
            title=title,
            deep_link=deep_link,
            body=body,
        )
