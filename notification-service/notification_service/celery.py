"""
Celery configuration for notification service.
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')

# Create Celery app
app = Celery('notification_service')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Optional: Configure additional Celery settings
app.conf.update(
    # Task routing
    task_routes={
        'core.tasks.send_notification': {'queue': 'notifications'},
        'core.tasks.batch_send_notifications': {'queue': 'bulk_notifications'},
        'infrastructure.tasks.cleanup_old_logs': {'queue': 'maintenance'},
    },
    
    # Task execution settings
    task_always_eager=False,  # Set to True for synchronous execution in tests
    task_eager_propagates=True,
    task_ignore_result=False,
    task_track_started=True,
    
    # Message routing
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task execution time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
)


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'


if __name__ == '__main__':
    app.start()