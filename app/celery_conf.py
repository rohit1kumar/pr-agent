from celery import Celery
from app.config import settings

celery_app = Celery(__name__, broker=settings.REDIS_URL, backend=settings.REDIS_URL)
