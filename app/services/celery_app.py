from celery import Celery
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Créer l'instance Celery
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

# Configuration Celery
celery_app.conf.update(
    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Task routing
    task_routes={
        'app.services.tasks.content_generation.*': {'queue': 'content_generation'},
        'app.services.tasks.content_formatting.*': {'queue': 'content_formatting'},
        'app.services.tasks.content_publishing.*': {'queue': 'content_publishing'},
        'app.services.tasks.image_generation.*': {'queue': 'image_generation'},
    },

    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            'TCP_KEEPINTVL': 1,
            'TCP_KEEPCNT': 3,
            'TCP_KEEPIDLE': 1,
        },
    },

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'app.services.tasks'
])

logger.info("Celery app configured successfully")

if __name__ == '__main__':
    celery_app.start()