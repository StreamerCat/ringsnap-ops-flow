"""Execution flow wrappers for safe PR-generating workflows."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class WorkflowRunSummary:
    trigger: str
    findings: list[str]
    files_changed: list[str]
    tests_run: list[str]
    pr_opened: bool
    blocked_actions: list[str]
    next_step: str


@dataclass(frozen=True)
class WorkflowRunResult:
    outcome: ExecutionOutcome
    summary: WorkflowRunSummary


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


def run_post_deploy_site_quality_guard(
    *,
    trigger: str,
    findings: list[str],
    path: str,
    updated_content: str,
    summary: str,
    deployed_urls: list[str],
) -> WorkflowRunResult:
    """Low-risk, post-deploy quality guard that can auto-open a scoped PR."""
    plan = build_low_risk_marketing_plan(path=path, updated_content=updated_content, summary=summary)
    outcome = _lane().execute(
        plan,
        allow_pr_only_apply=False,
        validate_execute=not settings.ops_execution_dry_run,
    )
    blocked_actions = []
    if outcome.status in {"blocked", "requires_human_review", "validation_failed"}:
        blocked_actions.append(outcome.reason)

    tests_run = [result.command for result in outcome.validations]
    next_step = "Monitor PR and merge after review." if outcome.pr_url else "Escalate to operator for manual investigation."
    enriched_findings = findings + [f"Deployed URLs inspected: {', '.join(deployed_urls)}"]
    run_summary = WorkflowRunSummary(
        trigger=trigger,
        findings=enriched_findings,
        files_changed=[patch.path for patch in plan.patches],
        tests_run=tests_run,
        pr_opened=bool(outcome.pr_url),
        blocked_actions=blocked_actions,
        next_step=next_step,
    )
    return WorkflowRunResult(outcome=outcome, summary=run_summary)


def run_critical_flow_recovery_assistant(
    *,
    trigger: str,
    findings: list[str],
    path: str,
    updated_content: str,
    summary: str,
    human_approved_patch: bool,
) -> WorkflowRunResult:
    """PR-only recovery assistant for critical activation and onboarding failures."""
    outcome = run_activation_pr_only_workflow(
        path=path,
        updated_content=updated_content,
        summary=summary,
        human_approved_patch=human_approved_patch,
    )
    blocked_actions = []
    if outcome.status in {"blocked", "requires_human_review", "validation_failed"}:
        blocked_actions.append(outcome.reason)

    tests_run = [result.command for result in outcome.validations]
    next_step = "Operator review required before merge/deploy." if outcome.pr_url else "Human triage required: patch not promoted to PR."
    run_summary = WorkflowRunSummary(
        trigger=trigger,
        findings=findings,
        files_changed=[path],
        tests_run=tests_run,
        pr_opened=bool(outcome.pr_url),
        blocked_actions=blocked_actions,
        next_step=next_step,
    )
    return WorkflowRunResult(outcome=outcome, summary=run_summary)
