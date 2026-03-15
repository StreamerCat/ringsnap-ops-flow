"""Unit tests for GitHubPRWriter request guards."""

import pytest

from ringsnap_ops_flow.execution.github_pr_writer import GitHubPRWriter, GitHubWriteError


def test_writer_requires_token():
    writer = GitHubPRWriter(owner="StreamerCat", repo="ringsnap", token="")
    with pytest.raises(GitHubWriteError, match="GITHUB_TOKEN missing"):
        writer.get_branch_sha("main")


def test_writer_requires_owner_repo():
    writer = GitHubPRWriter(owner="", repo="", token="token")
    with pytest.raises(GitHubWriteError, match="owner/repo not configured"):
        writer.get_branch_sha("main")
