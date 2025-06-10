from celery import Celery
import os

# Initialize Celery
celery = Celery(
    'app.tasks',
    broker=os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/'),
    backend='redis://redis:6379/0',
    include=['app.tasks.currency']
)

# Optional configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
) 