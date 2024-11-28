import ssl
from celery import Celery
from app.config import settings

ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}
connection_url = settings.REDIS_URL

if connection_url.startswith("rediss://"):
    ssl_options = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(__name__)

celery_app.conf.update(
    broker_url=connection_url,
    result_backend=connection_url,
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    broker_connection_retry_on_startup=True,
)
