import re
import logging
from typing import List, Dict, Optional, Any
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository


class GitHubService:
    """Service for interacting with GitHub repositories and pull requests."""

    def __init__(self, token: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.client = Github(token) if token else Github()

    def _parse_repo_url(self, repo_url: str) -> tuple:
        """
        Parse GitHub repository URL into owner and repo name.
        """
        match = re.match(r"https?://github.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError("Invalid GitHub repository URL")
        return match.groups()

    def get_pr_files(self, repo_url: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Fetch files with changes from a specific pull request.
        """
        try:
            self.logger.info(f"Fetching files from PR #{pr_number} in {repo_url}")
            owner, repo_name = self._parse_repo_url(repo_url)
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)

            files = []
            for file in pr.get_files():
                files.append(
                    {
                        "name": file.filename,
                        "content": file.patch,
                        "status": file.status,
                    }
                )
            self.logger.info(f"Successfully fetched {len(files)} files from PR")
            return files

        except Exception as e:
            self.logger.error(f"Error fetching PR files: {str(e)}")
            raise
