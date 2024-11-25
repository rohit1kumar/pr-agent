from fastapi import FastAPI, HTTPException, status
import logging
from schema import PRAnalysisRequest, TaskStatusResponse, AnalysisResultResponse

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


        return {
            "task_id": "task",
            "status": "pending",
            "message": "Analysis task created successfully",
        }

    except Exception as e:
        logger.error(f"Error creating analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_task_status(task_id: str):
    """Get the status of an analysis task."""
    pass


@app.get(
    "/results/{task_id}",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_results(task_id: str):
    """Get the results of an analysis task."""
    pass
