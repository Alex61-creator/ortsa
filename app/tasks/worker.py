import asyncio

from celery import Celery
from celery.signals import worker_process_shutdown

from app.core.config import settings

celery_app = Celery(
    "astro_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.report_generation",
        "app.tasks.report_notifications",
        "app.tasks.synastry_generation",
        "app.tasks.cleanup",
        "app.tasks.subscription_renewal",
        "app.tasks.monthly_digest",
        "app.tasks.subscription_finalize",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=40 * 60,       # hard kill: 40 мин (LLM 300s × retries + PDF + email)
    task_soft_time_limit=35 * 60,  # graceful: 35 мин → SoftTimeLimitExceeded перехватывается в задаче
    task_acks_late=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.report_generation.*": {"queue": "heavy"},
        "app.tasks.synastry_generation.*": {"queue": "heavy"},
        "app.tasks.report_notifications.*": {"queue": "io"},
        "app.tasks.monthly_digest.*": {"queue": "io"},
        "app.tasks.subscription_renewal.*": {"queue": "io"},
        "app.tasks.subscription_finalize.*": {"queue": "io"},
        "app.tasks.cleanup.*": {"queue": "io"},
    },
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=3600,
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cancel-expired-orders": {
        "task": "app.tasks.cleanup.cancel_expired_orders",
        "schedule": crontab(minute=0, hour="*/1"),
    },
    "cleanup-old-files": {
        "task": "app.tasks.cleanup.cleanup_storage",
        "schedule": crontab(minute=0, hour=3),
    },
    "subscription-renewals": {
        "task": "app.tasks.subscription_renewal.renew_due_subscriptions",
        "schedule": crontab(minute=15, hour="*/6"),
    },
    "monthly-pro-digest": {
        "task": "app.tasks.monthly_digest.run_monthly_pro_digests",
        "schedule": crontab(minute=0, hour=8, day_of_month=1),
    },
    "finalize-subscriptions-period-end": {
        "task": "app.tasks.subscription_finalize.finalize_subscriptions_at_period_end",
        "schedule": crontab(minute=30, hour=4),
    },
}


@worker_process_shutdown.connect
def _dispose_async_engine(**kwargs):
    from app.db.session import engine

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(engine.dispose())
        loop.close()
    except Exception:
        pass