from pydantic import BaseModel, Field
from typing import Any, List
from enum import Enum


# API Request/Response Schemas
class PRAnalysisRequest(BaseModel):
    repo_url: str
    pr_number: int
    github_token: str | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str


class AnalysisResultResponse(BaseModel):
    task_id: str
    status: str
    results: dict[str, Any]


