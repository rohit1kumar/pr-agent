from celery import Celery
from app.config import settings
import ssl

ssl_options = {}
if settings.REDIS_URL.startswith("rediss://"):
    ssl_options = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(__name__, broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    broker_connection_retry_on_startup=True,
)
