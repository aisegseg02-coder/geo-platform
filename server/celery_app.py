import os
from celery import Celery
from kombu import Queue, Exchange

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery app
celery_app = Celery(
    'geo_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['server.tasks']
)

# 1. Advanced Task Routing & Priority Queues
celery_app.conf.task_queues = (
    Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('low_priority', Exchange('low_priority'), routing_key='low_priority'),
    Queue('dead_letter', Exchange('dead_letter'), routing_key='dead_letter'), # Failed jobs log here
)

celery_app.conf.update(
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    
    # 2. Worker & Failure Recovery Limits
    task_time_limit=3600,       # Kill task if it exceeds 1 hour
    task_soft_time_limit=3500,  # Raise SoftTimeLimitExceeded gracefully
    
    # 3. Connection limits logic 
    broker_pool_limit=10, 
    redis_max_connections=20,
    
    # 4. Advanced Retry & Backoff Configuration applied at task level globally
    task_annotations={
        '*': {
            'autoretry_for': (Exception,),
            'retry_backoff': True,          # Exponential backoff
            'retry_backoff_max': 600,       # Max backoff 10 mins
            'max_retries': 3,               # Fail gracefully after 3 attempts
            'retry_jitter': True            # Prevent retry thundering herd
        }
    }
)
