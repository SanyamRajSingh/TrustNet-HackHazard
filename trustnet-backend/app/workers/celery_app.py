"""
Celery Configuration
Background task processing for Render Workflows.
"""

from celery import Celery
from celery.signals import task_failure, task_success

from config import settings

celery_app = Celery(
    "trustnet",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "daily-intelligence-refresh": {
            "task": "app.workers.tasks.daily_refresh",
            "schedule": 86400.0,  # 24 hours
        },
        "community-score-recalc": {
            "task": "app.workers.tasks.community_recalc",
            "schedule": 1800.0,  # 30 minutes
        },
        "blockchain-sync": {
            "task": "app.workers.tasks.blockchain_sync",
            "schedule": 3600.0,  # 1 hour
        },
    },
)


@task_success.connect
def handle_success(sender=None, result=None, **kwargs):
    import structlog
    logger = structlog.get_logger()
    logger.info("celery.task_success", task=sender.name if sender else "unknown")


@task_failure.connect
def handle_failure(sender=None, exception=None, **kwargs):
    import structlog
    logger = structlog.get_logger()
    logger.error("celery.task_failure", task=sender.name if sender else "unknown", error=str(exception))
