"""Execution flow wrappers for safe PR-generating workflows."""

from __future__ import annotations

from ..config import settings
from ..execution.github_pr_writer import GitHubPRWriter
from ..execution.policy import AutonomyPolicy
from ..execution.validator import TargetedValidator
from ..execution.proposal_generator import proposal_from_diagnosis_json
from ..execution.workflows import (
    ExecutionOutcome,
    build_activation_failure_pr_only_plan,
    build_low_risk_marketing_plan,
    RepoExecutionLane,
)


def _lane() -> RepoExecutionLane:
    policy = AutonomyPolicy.from_default_file()
    validator = TargetedValidator()
    writer = GitHubPRWriter(
        owner=settings.ringsnap_repo_owner,
        repo=settings.ringsnap_repo_name,
        token=settings.github_token,
    )
    return RepoExecutionLane(policy=policy, validator=validator, writer=writer)


def run_low_risk_auto_pr_workflow(*, path: str, updated_content: str, summary: str) -> ExecutionOutcome:
    plan = build_low_risk_marketing_plan(path=path, updated_content=updated_content, summary=summary)
    return _lane().execute(
        plan,
        allow_pr_only_apply=False,
        validate_execute=not settings.ops_execution_dry_run,
    )


def run_activation_pr_only_workflow(
    *,
    path: str,
    updated_content: str,
    summary: str,
    human_approved_patch: bool,
) -> ExecutionOutcome:
    plan = build_activation_failure_pr_only_plan(path=path, updated_content=updated_content, summary=summary)
    return _lane().execute(
        plan,
        allow_pr_only_apply=human_approved_patch,
        validate_execute=not settings.ops_execution_dry_run,
    )


def run_diagnosis_execution_workflow(
    *,
    diagnosis_json: str,
    human_approved_patch: bool = False,
) -> ExecutionOutcome:
    """Convert diagnosis JSON into PatchPlan and route through policy-gated execution lane."""
    proposal = proposal_from_diagnosis_json(diagnosis_json)
    return _lane().execute(
        proposal.plan,
        allow_pr_only_apply=human_approved_patch,
        validate_execute=not settings.ops_execution_dry_run,
    )
