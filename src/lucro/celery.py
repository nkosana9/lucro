import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lucro.settings")

app = Celery("lucro")

# Load configuration from Django settings, all config keys will be made uppercase
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working correctly."""
    print(f"Request: {self.request!r}")
