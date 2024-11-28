from pydantic import BaseModel, Field
from typing import Any, List
from enum import Enum


# API Request/Response schema given below
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


# LLM response schema
class IssueTypeEnums(str, Enum):
    style = "style"
    bug = "bug"
    performance = "performance"
    best_practice = "best_practice"


class IssueSeverityEnums(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Issue(BaseModel):
    type: IssueTypeEnums = Field(
        description="Type of issue found, choose from style, bug, performance, best_practice"
    )
    line: int = Field(description="Line number where the issue is found")
    description: str = Field(description="Detailed description of the issue")
    suggestion: str = Field(description="Specific suggestion for improvement")
    severity: IssueSeverityEnums = Field(
        description="Severity level of the issue, choose from critical, high, medium, low"
    )


class LLMResponseSchema(BaseModel):
    issues: List[Issue] = Field(description="List of code analysis issues")
