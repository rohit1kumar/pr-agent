import os
import ssl
from celery import Celery
from dotenv import load_dotenv
from celery.utils.log import get_task_logger
from app.services.gh import GitHubService
from app.services.analyzer import AICodeAnalysisService

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
    try:
        logger.info(f"Starting code analysis for PR #{pr_number}")

        # Fetch files from PR
        gh = GitHubService(github_token)
        pr_files = gh.get_pr_files(repo_url, pr_number)

        analysis_results = []
        total_issues = 0
        critical_issues = 0

        ai_analyser = AICodeAnalysisService()

        # Analyze each file
        for pr_file in pr_files:
            data = ai_analyser.analyze_file(
                pr_file["content"], pr_file["name"], pr_file["status"]
            )
            analysis_results.append(data)

            # Update Summary
            total_issues += len(data["issues"])
            for issue in data["issues"]:
                if issue["severity"] == "critical":
                    critical_issues += 1

        # Create final report
        logger.info(f"Code analysis completed for PR #{pr_number}")
        return {
            "files": analysis_results,
            "summary": {
                "total_files": len(pr_files),
                "total_issues": total_issues,
                "critical_issues": critical_issues,
            },
        }

    except Exception as e:
        logger.error(f"Error in code analysis: {str(e)}")
        raise
