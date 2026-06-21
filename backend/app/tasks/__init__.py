import logging

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logging.getLogger("celery").setLevel(logging.WARNING)
logging.getLogger("celery.beat").setLevel(logging.WARNING)
logging.getLogger("celery.worker").setLevel(logging.WARNING)
logging.getLogger("celery.app.trace").setLevel(logging.WARNING)

redis_url = settings.REDIS_URL

celery = Celery(
    "app.tasks",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.tasks.sync_products",
        "app.tasks.sync_recipes",
        "app.tasks.execute_consumption",
        "app.tasks.range_check",
        "app.tasks.day_check",
        "app.tasks.email",
        "app.tasks.create_meal_plan_batch",
        "app.tasks.recovery_sweep_meal_plans",
        "app.tasks.sync_stock_expiry",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Kyiv",
    enable_utc=True,
    worker_hijack_root_logger=True,
    worker_log_color=False,
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=300,
    task_time_limit=360,
    beat_schedule={
        "sync-all-products-every-4h": {
            "task": "app.tasks.sync_products.sync_all_products",
            "schedule": crontab(hour="*/4", minute=0),
        },
        "sync-all-recipes-every-6h": {
            "task": "app.tasks.sync_recipes.sync_all_recipes",
            "schedule": crontab(hour="*/6", minute=10),
        },
        "recovery-sweep-meal-plans-every-5min": {
            "task": "app.tasks.recovery_sweep_meal_plans.recovery_sweep_meal_plans_task",
            "schedule": crontab(minute="*/5"),
        },
        "sync-stock-expiry-every-4h": {
            "task": "app.tasks.sync_stock_expiry.sync_all_stock_expiry",
            "schedule": crontab(hour="*/4", minute=20),
        },
    },
)
