"""GitHub write-side helper for creating branches, commits, and PRs."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx


class GitHubWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class PullRequestRef:
    number: int
    url: str


class GitHubPRWriter:
    api_base = "https://api.github.com"

    def __init__(self, owner: str, repo: str, token: str) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {self.token}",
        }

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if not self.token:
            raise GitHubWriteError("GITHUB_TOKEN missing for write operations")
        if not self.owner or not self.repo:
            raise GitHubWriteError("GitHub owner/repo not configured")

        url = f"{self.api_base}{path}"
        with httpx.Client(timeout=20.0, headers=self._headers()) as client:
            response = client.request(method, url, json=payload)

        if response.status_code >= 400:
            raise GitHubWriteError(f"GitHub write request failed ({response.status_code}) for {path}: {response.text[:180]}")
        return response.json() if response.content else {}

    def get_branch_sha(self, branch: str) -> str:
        data = self._request("GET", f"/repos/{self.owner}/{self.repo}/git/ref/heads/{branch}")
        return data["object"]["sha"]

    def create_branch(self, branch: str, from_branch: str) -> None:
        base_sha = self.get_branch_sha(from_branch)
        self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/git/refs",
            payload={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )

    def get_file_sha(self, path: str, branch: str) -> str | None:
        try:
            data = self._request("GET", f"/repos/{self.owner}/{self.repo}/contents/{path}?ref={branch}")
            return data.get("sha")
        except GitHubWriteError as exc:
            if "(404)" in str(exc):
                return None
            raise

    def upsert_file(self, *, branch: str, path: str, content: str, commit_message: str) -> None:
        current_sha = self.get_file_sha(path, branch)
        payload = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if current_sha:
            payload["sha"] = current_sha

        self._request("PUT", f"/repos/{self.owner}/{self.repo}/contents/{path}", payload=payload)

    def create_pr(self, *, head_branch: str, base_branch: str, title: str, body: str, draft: bool = True) -> PullRequestRef:
        data = self._request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/pulls",
            payload={
                "title": title,
                "head": head_branch,
                "base": base_branch,
                "body": body,
                "draft": draft,
            },
        )
        return PullRequestRef(number=data["number"], url=data["html_url"])
