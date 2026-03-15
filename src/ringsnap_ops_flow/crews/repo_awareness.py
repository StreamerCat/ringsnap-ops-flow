"""Shared repo-awareness helpers for crew agents and task prompts."""

from __future__ import annotations

from crewai import Agent

from ..config import settings
from ..tools.github_repo_tool import GitHubRepoTool


def repo_context_hint() -> str:
    return (
        f"RingSnap repo target: {settings.ringsnap_repo or '(not configured)'} @ "
        f"{settings.ringsnap_branch}. App URL: {settings.ringsnap_app_url}. "
        f"Marketing URL: {settings.ringsnap_marketing_url}."
    )


def repo_inspection_block(scenario: str) -> str:
    """Standard prompt block for evidence-driven repo-aware analysis tasks."""
    return (
        "Repo-aware requirement:\n"
        "- Before final diagnosis, inspect relevant RingSnap app repo files using inspect_ringsnap_repo.\n"
        "- If repo access is unavailable, explicitly say so and lower confidence.\n"
        "- Separate runtime evidence from repo evidence; do not speculate without evidence.\n"
        f"- Focus repo inspection on files most relevant to: {scenario}.\n"
        "- Include these JSON fields in output:\n"
        "  - repo_files_checked (list of file paths)\n"
        "  - repo_evidence (list of concrete findings from files)\n"
        "  - likely_code_path (string for most likely file/module involved)\n"
        "  - confidence ('low'|'medium'|'high')\n"
        "  - recommended_next_validation (list of practical validation steps)\n"
    )


def maybe_repo_tools(enabled: bool) -> list:
    return [GitHubRepoTool()] if enabled else []


def build_agent(*, role: str, goal: str, backstory: str, llm, enable_repo_read: bool) -> Agent:
    """Create agents consistently with optional read-only repo inspection capability."""
    repo_backstory = (
        f" {repo_context_hint()} Use repo inspection only for diagnosis/verification and never for destructive actions."
        if enable_repo_read
        else ""
    )
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory + repo_backstory,
        llm=llm,
        verbose=False,
        allow_delegation=False,
        tools=maybe_repo_tools(enable_repo_read),
    )
