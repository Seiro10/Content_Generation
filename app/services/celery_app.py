from celery import Celery
from app.config.settings import settings
import logging
import sys

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

celery_app = Celery(
    "social_media_publisher",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        'app.services.tasks.content_generation',
        'app.services.tasks.content_formatting',
        'app.services.tasks.content_publishing',
        'app.services.tasks.image_generation'
    ]
)

celery_app.conf.update(
    timezone='UTC',
    enable_utc=True,

    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    task_routes={
        'app.services.tasks.content_generation.*': {'queue': 'content_generation'},
        'app.services.tasks.content_formatting.*': {'queue': 'content_formatting'},
        'app.services.tasks.content_publishing.*': {'queue': 'content_publishing'},
        'app.services.tasks.image_generation.*': {'queue': 'image_generation'},
    },

    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,  # ✅ éviter les doubles en cas de crash

    result_expires=3600,
    result_backend_transport_options={
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            'TCP_KEEPINTVL': 1,
            'TCP_KEEPCNT': 3,
            'TCP_KEEPIDLE': 1,
        },
    },

    task_default_retry_delay=60,
    task_max_retries=3,

    broker_connection_retry_on_startup=True,  # ✅ pour compat Celery 6

    worker_send_task_events=True,
    task_send_sent_event=True,
)

celery_app.autodiscover_tasks([
    'app.services.tasks'
])

logger.info("Celery app configured successfully")

if __name__ == '__main__':
    celery_app.start()
