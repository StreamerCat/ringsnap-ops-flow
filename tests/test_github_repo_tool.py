"""Unit tests for GitHubRepoTool."""

import json

from ringsnap_ops_flow.tools.github_repo_tool import GitHubRepoTool
from ringsnap_ops_flow.utils.github_repo_reader import GitHubRepoAccessError, RepoFile


class _FakeReader:
    def list_files(self, path_prefix: str = "", limit: int = 100):
        return ["src/a.ts", "src/b.ts"][:limit]

    def read_file(self, path: str):
        return RepoFile(path=path, content="const x = 1", sha="deadbeef")


def test_tool_list_files_success(monkeypatch):
    tool = GitHubRepoTool()
    monkeypatch.setattr(tool, "_reader", lambda: _FakeReader())

    payload = json.loads(tool._run(action="list_files", path="src/", limit=2))
    assert payload["status"] == "ok"
    assert payload["count"] == 2
    assert payload["files"] == ["src/a.ts", "src/b.ts"]


def test_tool_read_file_requires_path():
    tool = GitHubRepoTool()
    payload = json.loads(tool._run(action="read_file", path=""))
    assert payload["status"] == "error"


def test_tool_graceful_unavailable_on_repo_access_error(monkeypatch):
    tool = GitHubRepoTool()

    class _Raiser:
        def list_files(self, path_prefix: str = "", limit: int = 100):
            raise GitHubRepoAccessError("missing token")

    monkeypatch.setattr(tool, "_reader", lambda: _Raiser())

    payload = json.loads(tool._run(action="list_files", path="src/", limit=5))
    assert payload["status"] == "unavailable"
    assert "missing token" in payload["error"]
