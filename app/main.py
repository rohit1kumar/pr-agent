from fastapi import FastAPI, HTTPException, status
import logging
from app.schemas import PRAnalysisRequest, TaskStatusResponse, AnalysisResultResponse
from app.tasks import analyze_code_task
from celery.result import AsyncResult

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PR Agent API")


@app.post(
    "/analyze-pr",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskStatusResponse,
)
async def analyze_pr(request: PRAnalysisRequest):
    """Submit a PR for analysis."""
    try:
        logger.info(
            f"Received analysis request for PR #{request.pr_number} from {request.repo_url}"
        )
        task = analyze_code_task.delay(
            request.repo_url,
            request.pr_number,
            request.github_token,
        )
        logger.info(f"Analysis task created with ID: {task.id}")

        return {
            "task_id": task.id,
            "status": "PENDING",
        }

    except Exception as e:
        logger.error(f"Error creating analysis task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_task_status(task_id: str):
    """Get the status of an analysis task."""
    task = AsyncResult(task_id)

    return {
        "task_id": task.id,
        "status": task.status,
    }


@app.get(
    "/results/{task_id}",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_results(task_id: str):
    """Get the results of an analysis task."""

    task = AsyncResult(task_id)
    if task.status == "SUCCESS":
        return {
            "task_id": task.id,
            "status": task.status,
            "results": task.result,
        }

    return {
        "task_id": task.id,
        "status": task.status,
        "results": {},
    }
