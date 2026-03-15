"""Read-only GitHub repository access utilities for repo-aware crew tasks."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx


class GitHubRepoAccessError(RuntimeError):
    """Raised when repository access fails for a known operational reason."""


@dataclass(frozen=True)
class RepoFile:
    """Normalized file payload returned from GitHub."""

    path: str
    content: str
    sha: str


class GitHubRepoReader:
    """Minimal read-only GitHub API client for source inspection."""

    api_base = "https://api.github.com"

    def __init__(self, owner: str, repo: str, branch: str = "main", token: str = "") -> None:
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.token = token

    @property
    def is_configured(self) -> bool:
        return bool(self.owner and self.repo and self.token)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request_json(self, path: str, params: dict | None = None) -> dict:
        if not self.owner or not self.repo:
            raise GitHubRepoAccessError("Repository owner/repo not configured.")
        if not self.token:
            raise GitHubRepoAccessError("GITHUB_TOKEN is missing; repository inspection is unavailable.")

        url = f"{self.api_base}{path}"
        with httpx.Client(timeout=20.0, headers=self._headers()) as client:
            response = client.get(url, params=params)

        if response.status_code in {401, 403}:
            raise GitHubRepoAccessError("GitHub token is invalid or lacks repo read permissions.")
        if response.status_code == 404:
            raise GitHubRepoAccessError(f"Repository resource not found: {path}")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubRepoAccessError(f"GitHub API request failed ({response.status_code}): {path}") from exc

        return response.json()

    def list_files(self, path_prefix: str = "", limit: int = 100) -> list[str]:
        """List repository files from the git tree for quick discovery."""
        data = self._request_json(
            f"/repos/{self.owner}/{self.repo}/git/trees/{self.branch}",
            params={"recursive": "1"},
        )
        tree = data.get("tree", [])
        files = [item["path"] for item in tree if item.get("type") == "blob"]

        if path_prefix:
            files = [path for path in files if path.startswith(path_prefix)]

        return files[: max(1, limit)]

    def read_file(self, path: str) -> RepoFile:
        """Read a file from the configured branch and decode contents."""
        normalized_path = path.strip("/")
        payload = self._request_json(
            f"/repos/{self.owner}/{self.repo}/contents/{normalized_path}",
            params={"ref": self.branch},
        )

        if payload.get("type") != "file":
            raise GitHubRepoAccessError(f"Path is not a file: {normalized_path}")

        content = payload.get("content", "")
        encoding = payload.get("encoding")
        if encoding == "base64":
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        else:
            decoded = content

        return RepoFile(path=payload.get("path", normalized_path), content=decoded, sha=payload.get("sha", ""))
