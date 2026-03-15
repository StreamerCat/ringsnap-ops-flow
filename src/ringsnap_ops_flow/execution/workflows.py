"""Repo execution workflows: diagnose -> plan -> patch -> validate -> open PR."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .github_pr_writer import PullRequestRef
from .policy import AutonomyPolicy
from .validator import TargetedValidator, ValidationResult


@dataclass(frozen=True)
class FilePatch:
    path: str
    content: str


@dataclass(frozen=True)
class PatchPlan:
    change_class: str
    title: str
    summary: str
    patches: list[FilePatch]
    base_branch: str = "main"
    validation_class: str | None = None


@dataclass
class ExecutionOutcome:
    status: str
    mode: str
    reason: str
    branch: str = ""
    pr_number: int | None = None
    pr_url: str = ""
    validations: list[ValidationResult] = field(default_factory=list)


class RepoExecutionLane:
    """Safe patch execution lane backed by autonomy policy."""

    def __init__(self, *, policy: AutonomyPolicy, validator: TargetedValidator, writer):
        self.policy = policy
        self.validator = validator
        self.writer = writer

    def execute(
        self,
        plan: PatchPlan,
        *,
        allow_pr_only_apply: bool = False,
        validate_execute: bool = False,
    ) -> ExecutionOutcome:
        paths = [p.path for p in plan.patches]
        decision = self.policy.classify(plan.change_class, paths)

        if decision.mode == "blocked":
            return ExecutionOutcome(status="blocked", mode=decision.mode, reason=decision.reason)

        if decision.mode == "pr_only" and not allow_pr_only_apply:
            return ExecutionOutcome(status="requires_human_review", mode=decision.mode, reason=decision.reason)

        branch = self._branch_name(plan.change_class)
        self.writer.create_branch(branch=branch, from_branch=plan.base_branch)

        for patch in plan.patches:
            self.writer.upsert_file(
                branch=branch,
                path=patch.path,
                content=patch.content,
                commit_message=f"chore(ops): {plan.title}",
            )

        validation_class = plan.validation_class or plan.change_class
        validations = self.validator.run(validation_class, execute=validate_execute)
        if validations and any(not v.success for v in validations):
            return ExecutionOutcome(
                status="validation_failed",
                mode=decision.mode,
                reason="one or more validation commands failed",
                branch=branch,
                validations=validations,
            )

        pr = self.writer.create_pr(
            head_branch=branch,
            base_branch=plan.base_branch,
            title=plan.title,
            body=self._pr_body(plan, decision.reason, validations),
            draft=True,
        )
        return ExecutionOutcome(
            status="pr_opened",
            mode=decision.mode,
            reason=decision.reason,
            branch=branch,
            pr_number=pr.number,
            pr_url=pr.url,
            validations=validations,
        )

    @staticmethod
    def _branch_name(change_class: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        normalized = change_class.replace("_", "-")
        return f"ops/{normalized}-{stamp}"

    @staticmethod
    def _pr_body(plan: PatchPlan, policy_reason: str, validations: list[ValidationResult]) -> str:
        validation_lines = "\n".join(f"- `{v.command}`: {'pass' if v.success else 'fail'}" for v in validations) or "- none"
        files = "\n".join(f"- `{patch.path}`" for patch in plan.patches) or "- none"
        return (
            f"## Ops Auto-Generated PR\n"
            f"- Change class: `{plan.change_class}`\n"
            f"- Policy decision: {policy_reason}\n\n"
            f"### Summary\n{plan.summary}\n\n"
            f"### Files changed\n{files}\n\n"
            f"### Validation\n{validation_lines}\n"
        )


def build_low_risk_marketing_plan(*, path: str, updated_content: str, summary: str) -> PatchPlan:
    return PatchPlan(
        change_class="seo_meta_schema",
        title="fix(marketing): improve SEO metadata and schema hygiene",
        summary=summary,
        patches=[FilePatch(path=path, content=updated_content)],
    )


def build_activation_failure_pr_only_plan(*, path: str, updated_content: str, summary: str) -> PatchPlan:
    return PatchPlan(
        change_class="activation_failure_recovery",
        title="fix(activation): harden failure handling and diagnostics",
        summary=summary,
        patches=[FilePatch(path=path, content=updated_content)],
    )
