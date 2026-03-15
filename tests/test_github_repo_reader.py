"""Unit tests for GitHubRepoReader."""

import base64

import pytest

from ringsnap_ops_flow.utils.github_repo_reader import GitHubRepoAccessError, GitHubRepoReader


def test_reader_requires_token_for_api_calls():
    reader = GitHubRepoReader(owner="StreamerCat", repo="ringsnap", branch="main", token="")
    with pytest.raises(GitHubRepoAccessError, match="GITHUB_TOKEN is missing"):
        reader.list_files()


def test_list_files_filters_and_limits(monkeypatch):
    reader = GitHubRepoReader(owner="StreamerCat", repo="ringsnap", branch="main", token="token")

    def fake_request_json(path, params=None):
        return {
            "tree": [
                {"path": "app/api/route.ts", "type": "blob"},
                {"path": "app/ui/button.tsx", "type": "blob"},
                {"path": "docs/readme.md", "type": "blob"},
                {"path": "app", "type": "tree"},
            ]
        }

    monkeypatch.setattr(reader, "_request_json", fake_request_json)
    files = reader.list_files(path_prefix="app/", limit=1)
    assert files == ["app/api/route.ts"]


def test_read_file_decodes_base64_content(monkeypatch):
    reader = GitHubRepoReader(owner="StreamerCat", repo="ringsnap", branch="main", token="token")
    encoded = base64.b64encode(b"export const enabled = true\n").decode()

    def fake_request_json(path, params=None):
        return {
            "type": "file",
            "path": "src/config.ts",
            "sha": "abc123",
            "encoding": "base64",
            "content": encoded,
        }

    monkeypatch.setattr(reader, "_request_json", fake_request_json)
    file_payload = reader.read_file("src/config.ts")

    assert file_payload.path == "src/config.ts"
    assert file_payload.sha == "abc123"
    assert "enabled = true" in file_payload.content
