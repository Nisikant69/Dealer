import os
from celery import Celery

# Get the broker URL from the environment variable we set in docker-compose
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create the Celery instance
celery_app = Celery(
    "dealership_ai",
    broker=broker_url,
    backend=result_backend_url,
    include=["app.workflow.tasks"]  # Point to your tasks file
)

celery_app.conf.update(
    task_track_started=True,
)