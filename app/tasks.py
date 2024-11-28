import os
import ssl
from celery import Celery
from dotenv import load_dotenv
from celery.utils.log import get_task_logger
from typing import Dict, Any, List, Optional
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
import base64
from langchain_openai import ChatOpenAI
import re
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from enum import Enum


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


CODE_ANALYSIS_PROMPT = """You are an expert code reviewer for GitHub pull requests, here + denotes added lines and - denotes removed lines. Analyze the following code for:
1. Code style and formatting issues
2. Potential bugs or errors
3. Performance improvements
4. Security concerns
5. Best practices violations

Language: {language}

Status of the file: {status}

Code to analyze:
```
{code_content}
```

Provide a detailed analysis in the following JSON format in very brief:
{{
    "issues": [
        {{
            "type": "style|bug|performance|best_practice",
            "line": <line_number>,
            "description": "Detailed description of the issue",
            "suggestion": "Specific suggestion for improvement",
            "severity": "critical|high|medium|low"
        }}
    ]
}}
"""


def get_code_analysis_prompt(code_content: str, language: str, status: str):
    prompt = ChatPromptTemplate.from_template(CODE_ANALYSIS_PROMPT)
    return prompt.format_messages(
        code_content=code_content,
        language=language,
        status=status,
    )


# LLM Response Schema
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


class Summary(BaseModel):
    total_issues: int = Field(description="Total number of issues found")
    critical_issues: int = Field(description="Number of critical issues found")
    total_files: int = Field(description="Total number of files analyzed")


class LLMResponseSchema(BaseModel):
    issues: List[Issue] = Field(description="List of code analysis issues")


def detect_language(filename: str) -> str:
    """Detect programming language based on file extension."""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".html": "HTML",
        ".css": "CSS",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
    }
    ext = "." + filename.split(".")[-1].lower()
    return extension_map.get(ext, "Unknown")


def analyze_file(file_content: str, filename: str, file_status: str)-> Dict[str, Any]:
    try:
        logger.info(f"Starting analysis for file: {filename}")

        # Detect programming language
        language = detect_language(filename)

        # Create prompt
        formated_prompt = get_code_analysis_prompt(
            file_content,
            language,
            file_status,
        )
        # Get analysis from LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.environ.get("OPENAI_API_KEY", None),
        )

        response = {}
        try:
            llm = llm.with_structured_output(LLMResponseSchema, method="json_mode")
            response = llm.invoke(formated_prompt)
            if isinstance(response, LLMResponseSchema):
                response = response.model_dump()

        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            response = {"issues": []}

        response["filename"] = filename  # type: ignore

        logger.info(f"Completed analysis for file: {filename}")
        return response

    except Exception as e:
        logger.error(f"Error in analyze_file: {str(e)}")
        raise


def fetch_pr_files(
    repo_url: str, pr_number: int, token: Optional[str] = None
) -> List[Dict[str, str]]:
    try:
        logger.info(f"Fetching files from PR #{pr_number} in {repo_url}")

        # Extract owner and repo from URL
        match = re.match(r"https?://github.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError("Invalid GitHub repository URL")

        owner, repo_name = match.groups()

        # Initialize GitHub client
        gh = Github(token) if token else Github()

        # Get repository and PR
        repo: Repository = gh.get_repo(f"{owner}/{repo_name}")
        pr: PullRequest = repo.get_pull(pr_number)

        files = []
        for file in pr.get_files():
            files.append(
                {
                    "name": file.filename,
                    "content": file.patch,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                }
            )
        logger.info(f"Successfully fetched {len(files)} files from PR")
        return files

    except Exception as e:
        logger.error(f"Error in fetch_pr_files: {str(e)}")
        raise


@celery_app.task(name="analyze_code_task")
def analyze_code_task(repo_url: str, pr_number: int, github_token: str | None = None):
    """Analyze the code in a PR using AI agent."""
    logger.info(f"Analyzing code for PR #{pr_number} from {repo_url}")
    try:
        logger.info(f"Starting code analysis for PR #{pr_number}")

        # Fetch files from PR
        pr_files = fetch_pr_files(repo_url, pr_number, github_token)

        # Analyze each file
        analysis_results = []
        total_issues = 0
        critical_issues = 0

        for pr_file in pr_files:
            result = analyze_file(
                pr_file["content"], pr_file["name"], pr_file["status"]
            )
            analysis_results.append(result)

            # Update totals
            total_issues += len(result["issues"])
            for issue in result["issues"]:
                if issue["severity"] == "critical":
                    critical_issues += 1

        # Create final report
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
