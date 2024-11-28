import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas import LLMResponseSchema


class AICodeAnalysisService:
    """Service for performing code analysis using LLM."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize LLM service with optional model specification.
        """
        self.logger = logging.getLogger(__name__)
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.1,
            api_key=self.api_key,  # type: ignore
        )

    def _detect_language(self, file_name: str) -> str:
        """
        Detect programming language based on file extension.
        """
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
        ext = "." + file_name.split(".")[-1].lower()
        return extension_map.get(ext, "Unknown")

    def _get_prompt(self, file_content: str, language: str, file_status: str) -> list:
        """
        Generate prompt for code analysis.
        """
        ANALYSIS_PROMPT = """You are an expert code reviewer for GitHub pull requests, here + denotes added lines and - denotes removed lines. Analyze the following code for:
        1. Code style and formatting issues
        2. Potential bugs or errors
        3. Performance improvements
        4. Best practices violations

        Language: {language}

        Status of the file: {file_status}

        Code to analyze:
        ```
        {file_content}
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

        prompt = ChatPromptTemplate.from_template(ANALYSIS_PROMPT)
        return prompt.format_messages(
            file_content=file_content,
            language=language,
            file_status=file_status,
        )

    def analyze_file(self, file_content: str, file_name: str, file_status: str) -> dict:
        """
        Analyze a single file using AI.
        """
        self.logger.info(f"Starting analysis for file: {file_name}")

        # Detect programming language
        language = self._detect_language(file_name)
        # Create prompts
        prompt = self._get_prompt(file_content, language, file_status)

        response = {}
        try:
            llm = self.llm.with_structured_output(LLMResponseSchema, method="json_mode")
            response = llm.invoke(prompt)
            if isinstance(response, LLMResponseSchema):
                response = response.model_dump()
        except Exception as e:
            self.logger.error(f"Error getting response from LLM: {e}")
            response = {"issues": []}

        response["filename"] = file_name  # type: ignore

        self.logger.info(f"Completed analysis for file: {file_name}")
        return response
