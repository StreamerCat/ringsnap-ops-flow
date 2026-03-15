"""Tests for execution flow wrappers."""

from ringsnap_ops_flow.flows import repo_execution_flow
from ringsnap_ops_flow.execution.workflows import ExecutionOutcome


class FakeLane:
    def __init__(self):
        self.calls = []

    def execute(self, plan, *, allow_pr_only_apply: bool = False, validate_execute: bool = False):
        self.calls.append((plan.change_class, allow_pr_only_apply, validate_execute))
        return ExecutionOutcome(status="pr_opened", mode="auto_patch", reason="ok", pr_number=1, pr_url="u")


def test_low_risk_flow_uses_auto_patch_defaults(monkeypatch):
    fake = FakeLane()
    monkeypatch.setattr(repo_execution_flow, "_lane", lambda: fake)

    repo_execution_flow.run_low_risk_auto_pr_workflow(
        path="docs/runbooks/incident.md",
        updated_content="x",
        summary="s",
    )
    assert fake.calls[0][0] == "seo_meta_schema"
    assert fake.calls[0][1] is False


def test_activation_flow_passes_human_approval(monkeypatch):
    fake = FakeLane()
    monkeypatch.setattr(repo_execution_flow, "_lane", lambda: fake)

    repo_execution_flow.run_activation_pr_only_workflow(
        path="src/ringsnap_ops_flow/crews/activation_recovery/tasks.py",
        updated_content="x",
        summary="s",
        human_approved_patch=True,
    )
    assert fake.calls[0][0] == "activation_failure_recovery"
    assert fake.calls[0][1] is True


def test_diagnosis_execution_workflow_routes_generated_plan(monkeypatch):
    fake = FakeLane()
    monkeypatch.setattr(repo_execution_flow, "_lane", lambda: fake)

    diagnosis_json = """
    {
      "change_class": "seo_meta_schema",
      "validation_class": "docs_runbooks_tests_config",
      "title": "fix(docs): update runbook",
      "summary": "Grounded in repo evidence",
      "scoped_files": [{"path": "docs/runbooks/incident.md", "content": "updated"}]
    }
    """

    repo_execution_flow.run_diagnosis_execution_workflow(
        diagnosis_json=diagnosis_json,
        human_approved_patch=False,
    )

    assert fake.calls[0][0] == "seo_meta_schema"
    assert fake.calls[0][1] is False
