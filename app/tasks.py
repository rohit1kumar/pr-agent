import os
import ssl
from celery import Celery
from dotenv import load_dotenv
from celery.utils.log import get_task_logger


load_dotenv()
logger = get_task_logger(__name__)
celery_app = Celery(__name__)

ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}
connection_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

if connection_url is None:
    raise ValueError("REDIS_URL environment variable must be set")

if connection_url.startswith("rediss://"):
    ssl_options = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app.conf.update(
    broker_url=connection_url,
    result_backend=connection_url,
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="analyze_code_task")
def analyze_code_task(repo_url: str, pr_number: int, github_token: str | None = None):
    """Analyze the code in a PR using AI agent."""
    logger.info(f"Analyzing code for PR #{pr_number} from {repo_url}")
    data = {
        "files": [
            {
                "name": "main.py",
                "issues": [
                    {
                        "type": "style",
                        "line": 15,
                        "description": "Line too long",
                        "suggestion": "Break line into multiple lines",
                    },
                    {
                        "type": "bug",
                        "line": 23,
                        "description": "Potential null pointer",
                        "suggestion": "Add null check",
                    },
                ],
            }
        ],
        "summary": {"total_files": 1, "total_issues": 2, "critical_issues": 1},
    }
    return True
