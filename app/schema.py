from pydantic import BaseModel
from typing import Any


class PRAnalysisRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: str | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str


class AnalysisResultResponse(BaseModel):
    task_id: str
    status: str
    results: dict[str, Any]
