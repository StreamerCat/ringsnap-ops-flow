"""Tests for repo execution lane orchestration."""

from ringsnap_ops_flow.execution.policy import AutonomyPolicy
from ringsnap_ops_flow.execution.validator import TargetedValidator, ValidationResult
from ringsnap_ops_flow.execution.workflows import (
    RepoExecutionLane,
    build_activation_failure_pr_only_plan,
    build_low_risk_marketing_plan,
)


class FakeWriter:
    def __init__(self):
        self.branches = []
        self.upserts = []
        self.prs = []

    def create_branch(self, branch: str, from_branch: str):
        self.branches.append((branch, from_branch))

    def upsert_file(self, *, branch: str, path: str, content: str, commit_message: str):
        self.upserts.append((branch, path, content, commit_message))

    def create_pr(self, *, head_branch: str, base_branch: str, title: str, body: str, draft: bool = True):
        self.prs.append((head_branch, base_branch, title, body, draft))
        class Ref:
            number = 42
            url = "https://example.test/pr/42"
        return Ref()


class FakeValidator(TargetedValidator):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls = []

    def run(self, change_class: str, *, execute: bool = False, workdir: str = "."):
        self.calls.append(change_class)
        ok = not self.should_fail
        return [ValidationResult(command="pytest -q", success=ok, output="stub")]


def test_low_risk_workflow_creates_branch_patch_and_pr():
    policy = AutonomyPolicy.from_default_file()
    writer = FakeWriter()
    lane = RepoExecutionLane(policy=policy, validator=FakeValidator(), writer=writer)

    plan = build_low_risk_marketing_plan(
        path="docs/runbooks/incident.md",
        updated_content="updated",
        summary="Improve SEO references in runbook docs.",
    )

    result = lane.execute(plan)
    assert result.status == "pr_opened"
    assert writer.branches
    assert writer.upserts
    assert writer.prs


def test_activation_workflow_is_pr_only_without_approval():
    policy = AutonomyPolicy.from_default_file()
    writer = FakeWriter()
    lane = RepoExecutionLane(policy=policy, validator=FakeValidator(), writer=writer)

    plan = build_activation_failure_pr_only_plan(
        path="src/ringsnap_ops_flow/crews/activation_recovery/tasks.py",
        updated_content="updated",
        summary="Harden activation failure diagnostics.",
    )

    result = lane.execute(plan, allow_pr_only_apply=False)
    assert result.status == "requires_human_review"
    assert not writer.branches


def test_validation_failure_blocks_pr_opening():
    policy = AutonomyPolicy.from_default_file()
    writer = FakeWriter()
    lane = RepoExecutionLane(policy=policy, validator=FakeValidator(should_fail=True), writer=writer)

    plan = build_low_risk_marketing_plan(
        path="docs/runbooks/incident.md",
        updated_content="updated",
        summary="Improve docs.",
    )

    result = lane.execute(plan)
    assert result.status == "validation_failed"
    assert not writer.prs


def test_validation_class_override_is_used_for_targeted_commands():
    policy = AutonomyPolicy.from_default_file()
    writer = FakeWriter()
    validator = FakeValidator()
    lane = RepoExecutionLane(policy=policy, validator=validator, writer=writer)

    plan = build_low_risk_marketing_plan(
        path="docs/runbooks/incident.md",
        updated_content="updated",
        summary="Improve docs.",
    )
    plan = type(plan)(
        change_class=plan.change_class,
        title=plan.title,
        summary=plan.summary,
        patches=plan.patches,
        base_branch=plan.base_branch,
        validation_class="docs_runbooks_tests_config",
    )

    lane.execute(plan)
    assert validator.calls == ["docs_runbooks_tests_config"]
