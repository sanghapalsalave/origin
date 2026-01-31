"""
Celery application configuration for background tasks.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "origin",
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_BACKEND,
    include=[
        "app.tasks.portfolio_analysis",
        "app.tasks.audio_standup",
        "app.tasks.syllabus_updates",
        "app.tasks.notifications",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "generate-audio-standups": {
        "task": "app.tasks.audio_standup.generate_standups",
        "schedule": 86400.0,  # Daily check for 7-day intervals
    },
    "update-syllabi": {
        "task": "app.tasks.syllabus_updates.update_syllabi",
        "schedule": 604800.0,  # Weekly
    },
    "rebalance-squads": {
        "task": "app.tasks.squad_matching.rebalance_squads",
        "schedule": 86400.0,  # Daily
    },
}
