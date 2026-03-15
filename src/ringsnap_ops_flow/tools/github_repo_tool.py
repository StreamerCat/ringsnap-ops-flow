"""CrewAI tool for read-only inspection of RingSnap app repository."""

from __future__ import annotations

import json
from typing import Literal, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config import settings
from ..utils.github_repo_reader import GitHubRepoAccessError, GitHubRepoReader


class GitHubRepoInput(BaseModel):
    action: Literal["list_files", "read_file"] = Field(description="Action to perform")
    path: str = Field(default="", description="File path (for read_file) or path prefix (for list_files)")
    limit: int = Field(default=30, ge=1, le=500, description="Max files to return when listing")


class GitHubRepoTool(BaseTool):
    """Read-only GitHub repository inspection for diagnosis and QA tasks."""

    name: str = "inspect_ringsnap_repo"
    description: str = (
        "Read files from the RingSnap app repository for evidence-based diagnosis. "
        "Supports action='list_files' and action='read_file'. Read-only."
    )
    args_schema: Type[BaseModel] = GitHubRepoInput

    def _reader(self) -> GitHubRepoReader:
        return GitHubRepoReader(
            owner=settings.ringsnap_repo_owner,
            repo=settings.ringsnap_repo_name,
            branch=settings.ringsnap_branch,
            token=settings.github_token,
        )

    def _run(self, action: str, path: str = "", limit: int = 30) -> str:
        try:
            reader = self._reader()
            if action == "list_files":
                files = reader.list_files(path_prefix=path, limit=limit)
                return json.dumps(
                    {
                        "status": "ok",
                        "action": action,
                        "path_prefix": path,
                        "count": len(files),
                        "files": files,
                    }
                )

            if action == "read_file":
                if not path:
                    return json.dumps({"status": "error", "error": "path is required for read_file"})

                file_payload = reader.read_file(path)
                return json.dumps(
                    {
                        "status": "ok",
                        "action": action,
                        "file": {
                            "path": file_payload.path,
                            "sha": file_payload.sha,
                            "content": file_payload.content,
                        },
                    }
                )

            return json.dumps({"status": "error", "error": f"unsupported action: {action}"})
        except GitHubRepoAccessError as exc:
            return json.dumps(
                {
                    "status": "unavailable",
                    "error": str(exc),
                    "owner": settings.ringsnap_repo_owner,
                    "repo": settings.ringsnap_repo_name,
                    "branch": settings.ringsnap_branch,
                }
            )
