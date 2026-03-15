"""Tests for automatic post-deploy guard event handling."""

import asyncio

from ringsnap_ops_flow.main import _process_event, _run_post_deploy_guard
from ringsnap_ops_flow.state import OpsEvent, OpsEventType


class FakeGate:
    def __init__(self):
        self.recorded = []

    def should_process(self, **_kwargs):
        return True, ""

    def record_execution(self, module_name: str, event_type: str, cost_usd: float = 0.0, entity_id=None):
        self.recorded.append((module_name, event_type, cost_usd, entity_id))


def test_run_post_deploy_guard_skips_when_patch_payload_missing(monkeypatch):
    called = []
    monkeypatch.setattr(
        "ringsnap_ops_flow.main.run_post_deploy_site_quality_guard",
        lambda **kwargs: called.append(kwargs),
    )

    event = OpsEvent(
        event_type=OpsEventType.DEPLOY_COMPLETED,
        payload={"findings": ["no-op"]},
    )
    _run_post_deploy_guard(event)

    assert called == []


def test_run_post_deploy_guard_executes_wrapper_and_emits_summary(monkeypatch):
    calls = []

    class Result:
        class summary:  # noqa: N801 - test shim
            trigger = "deploy_completed"
            findings = ["SEO regression"]
            files_changed = ["docs/runbooks/incident.md"]
            tests_run = ["npm run lint"]
            pr_opened = True
            blocked_actions = []
            next_step = "Monitor PR and merge after review."

    def _fake_runner(**kwargs):
        calls.append(kwargs)
        return Result()

    monkeypatch.setattr("ringsnap_ops_flow.main.run_post_deploy_site_quality_guard", _fake_runner)

    event = OpsEvent(
        event_type=OpsEventType.DEPLOY_COMPLETED,
        payload={
            "findings": ["SEO regression"],
            "deployed_urls": ["https://ringsnap.com"],
            "path": "docs/runbooks/incident.md",
            "updated_content": "updated",
            "summary": "Fix metadata guidance",
        },
    )
    _run_post_deploy_guard(event)

    assert calls[0]["trigger"] == "deploy_completed"
    assert calls[0]["deployed_urls"] == ["https://ringsnap.com"]


def test_process_event_routes_deploy_completed_to_post_deploy_guard(monkeypatch):
    fake_gate = FakeGate()
    monkeypatch.setattr("ringsnap_ops_flow.main.get_gate", lambda: fake_gate)

    called = []
    monkeypatch.setattr("ringsnap_ops_flow.main._run_post_deploy_guard", lambda event: called.append(event.event_type.value))

    event = OpsEvent(
        event_type=OpsEventType.DEPLOY_COMPLETED,
        source="deploy",
        entity_id="deploy_123",
        payload={"path": "docs/runbooks/incident.md", "updated_content": "updated"},
    )

    asyncio.run(_process_event(event))

    assert called == [OpsEventType.DEPLOY_COMPLETED.value]
    assert fake_gate.recorded[0][1] == OpsEventType.DEPLOY_COMPLETED.value
