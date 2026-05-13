from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "fastapi_kubeneat",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_store_eager_result=True,
    result_extended=True,
    timezone="Asia/Shanghai",
)
