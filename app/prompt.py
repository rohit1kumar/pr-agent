from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Any, List
from enum import Enum

CODE_ANALYSIS_PROMPT = """You are an expert code reviewer for GitHub pull requests, here + denotes added lines and - denotes removed lines. Analyze the following code for:
1. Code style and formatting issues
2. Potential bugs or errors
3. Performance improvements
4. Security concerns
5. Best practices violations

Language: {language}

status of the file: {status}

Code to analyze:
```
{code_content}
```

Provide a detailed analysis in the following JSON format:
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
