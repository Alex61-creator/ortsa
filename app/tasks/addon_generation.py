import asyncio

from celery import shared_task

from app.tasks.report_generation import _generate_report_async


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def generate_transit_month_task(self, order_id: int):
    return asyncio.run(_generate_report_async(order_id, self.request.id))


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def generate_compatibility_deep_dive_task(self, order_id: int):
    return asyncio.run(_generate_report_async(order_id, self.request.id))


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def generate_return_pack_task(self, order_id: int):
    return asyncio.run(_generate_report_async(order_id, self.request.id))
