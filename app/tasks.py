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


CODE_ANALYSIS_PROMPT = """You are an expert code reviewer. Analyze the following code for:
1. Code style and formatting issues
2. Potential bugs or errors
3. Performance improvements
4. Security concerns
5. Best practices violations

Code to analyze:
```
{code_content}
```

Language: {language}

Provide a detailed analysis in the following JSON format in very brief:
{{
    "issues": [
        {{
            "type": "style|bug|performance|security|best_practice",
            "line": <line_number>,
            "description": "Detailed description of the issue",
            "suggestion": "Specific suggestion for improvement",
            "severity": "critical|high|medium|low"
        }}
    ],
    "summary": {{
        "total_issues": <number>,
        "critical_issues": <number>,
        "overview": "Brief summary of main findings"
    }}
}}
"""


def get_code_analysis_prompt(code_content: str, language: str):
    prompt = ChatPromptTemplate.from_template(CODE_ANALYSIS_PROMPT)
    return prompt.format_messages(code_content=code_content, language=language)


# LLM Response Schema
class IssueTypeEnums(str, Enum):
    style = "style"
    bug = "bug"
    performance = "performance"
    security = "security"
    best_practice = "best_practice"


class IssueSeverityEnums(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Issue(BaseModel):
    type: IssueTypeEnums = Field(
        description="Type of issue found, choose from style, bug, performance, security, best_practice"
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
    overview: str = Field(description="Brief summary of main findings")


class LLMResponseSchema(BaseModel):
    issues: List[Issue] = Field(description="List of code analysis issues")
    summary: Summary = Field(description="Summary of code analysis")


def detect_language(filename: str) -> str:
    """Detect programming language based on file extension."""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".cs": "C#",
        ".html": "HTML",
        ".css": "CSS",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
    }
    ext = "." + filename.split(".")[-1].lower()
    return extension_map.get(ext, "Unknown")


def analyze_file(file_content: str, filename: str) -> Dict[str, Any]:
    try:
        logger.info(f"Starting analysis for file: {filename}")

        # Detect programming language
        language = detect_language(filename)

        # Create prompt
        formated_prompt = get_code_analysis_prompt(file_content, language)

        # Get analysis from LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.environ.get("OPENAI_API_KEY", None),
        )

        analysis_result = {}
        try:
            llm = llm.with_structured_output(LLMResponseSchema, method="json_mode")
            analysis_result = llm.invoke(formated_prompt)
            if isinstance(analysis_result, LLMResponseSchema):
                analysis_result = analysis_result.model_dump()

        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            analysis_result = {
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "critical_issues": 0,
                    "overview": "Error analyzing file",
                },
            }

        # Add file metadata
        analysis_result["file_info"] = {
            "name": filename,
            "language": language,
            "size_bytes": len(file_content),
        }

        logger.info(f"Completed analysis for file: {filename}")
        return analysis_result

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
        g = Github(token) if token else Github()

        # Get repository and PR
        repo: Repository = g.get_repo(f"{owner}/{repo_name}")
        pr: PullRequest = repo.get_pull(pr_number)

        files = []
        for file in pr.get_files():
            try:
                # Get file content
                content = repo.get_contents(file.filename, ref=pr.head.sha)
                if isinstance(content, list):
                    # Skip directories
                    continue

                # Decode content
                file_content = base64.b64decode(content.content).decode("utf-8")

                files.append(
                    {
                        "name": file.filename,
                        "content": file_content,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Error fetching content for file {file.filename}: {str(e)}"
                )
                continue

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

        for file_info in pr_files:
            result = analyze_file(file_info["content"], file_info["name"])
            analysis_results.append(result)

            # Update totals
            total_issues += result["summary"]["total_issues"]
            critical_issues += result["summary"]["critical_issues"]

        # Create final report
        final_result = {
            "files": analysis_results,
            "summary": {
                "total_files": len(pr_files),
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "overview": f"Analyzed {len(pr_files)} files, found {total_issues} issues ({critical_issues} critical)",
            },
        }
        return final_result

    except Exception as e:
        logger.error(f"Error in code analysis: {str(e)}")
        raise
