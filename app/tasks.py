import os
from dotenv import load_dotenv
from celery import Celery
from celery.utils.log import get_task_logger
import ssl


logger = get_task_logger(__name__)
load_dotenv()

celery_app = Celery(__name__)


ssl_options = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
celery_app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="analyze_code_task")
def analyze_code_task(repo_url: str, pr_number: int, github_token: str | None = None):
    """Analyze the code in a PR using AI agent."""
    logger.info(f"Analyzing code for PR #{pr_number} from {repo_url}")

    return True
