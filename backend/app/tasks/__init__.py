import os
from celery import Celery
from celery.schedules import crontab

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')

celery = Celery(
    'app.tasks',
    broker=redis_url,
    backend=redis_url,
    include=[
        'app.tasks.sync_products',
    ]
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Kyiv',
    enable_utc=True,
    beat_schedule={
        'sync-all-products-daily': {
            'task': 'app.tasks.sync_products.sync_all_products',
            'schedule': crontab(hour=4, minute=0),
        },
    },
)
