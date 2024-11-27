import os
from pydantic import SecretStr, ValidationError
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
import base64
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import re
import logging
from app.prompt import get_code_analysis_prompt
from schema import LLMResponseSchema

load_dotenv()
logger = logging.getLogger(__name__)


def detect_language(filename: str) -> str:
    """Detect programming language based on file extension."""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
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
            api_key=SecretStr(os.environ.get("OPENAI_API_KEY", None)),
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
    """
    Fetch files from a GitHub PR.

    Args:
        repo_url: URL of the GitHub repository
        pr_number: PR number to analyze
        token: GitHub access token (optional)

    Returns:
        List of dicts containing file information and content
    """
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


if __name__ == "__main__":
    repo_url = "https://github.com/rohit1kumar/linked-note"
    resp = analyze_code_task(repo_url=repo_url, pr_number=1)
    # print json
    import json

    print(json.dumps(resp, indent=2))
