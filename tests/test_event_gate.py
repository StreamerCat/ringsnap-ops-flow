"""
Golden tests for EventGate — the central CrewAI invocation guard.
These tests protect the core gating logic.
Do not modify behavior without updating these tests first.
"""

import time
import pytest
from ringsnap_ops_flow.event_gate import EventGate, ALLOWED_EVENTS
from ringsnap_ops_flow.state import OpsEventType


def test_allowed_events_set_matches_enum():
    """All OpsEventType values must be in ALLOWED_EVENTS."""
    for event_type in OpsEventType:
        assert event_type.value in ALLOWED_EVENTS, f"{event_type.value} not in ALLOWED_EVENTS"


def test_non_allowlisted_event_dropped(event_gate):
    """Non-allowlisted events must always be dropped."""
    allowed, reason = event_gate.should_process("some_random_event", entity_id="abc123")
    assert allowed is False
    assert reason == "not_in_allowlist"


def test_allowlisted_event_passes(event_gate):
    """Allowlisted events pass when no other limits are hit."""
    allowed, reason = event_gate.should_process(
        OpsEventType.QUALIFIED_LEAD.value,
        entity_id="lead_001",
    )
    assert allowed is True
    assert reason == ""


def test_debounce_blocks_repeated_event(event_gate):
    """Same event + entity within debounce window must be dropped."""
    # First call passes
    allowed1, _ = event_gate.should_process(
        OpsEventType.PAYMENT_FAILURE.value,
        entity_id="account_abc",
    )
    assert allowed1 is True

    # Second call immediately after is debounced
    allowed2, reason2 = event_gate.should_process(
        OpsEventType.PAYMENT_FAILURE.value,
        entity_id="account_abc",
    )
    assert allowed2 is False
    assert "debounce" in reason2


def test_debounce_different_entities_both_pass(event_gate):
    """Different entity IDs should not debounce each other."""
    allowed1, _ = event_gate.should_process(
        OpsEventType.PAYMENT_FAILURE.value,
        entity_id="account_aaa",
    )
    allowed2, _ = event_gate.should_process(
        OpsEventType.PAYMENT_FAILURE.value,
        entity_id="account_bbb",
    )
    assert allowed1 is True
    assert allowed2 is True


def test_daily_budget_blocks_when_exceeded(event_gate):
    """Events must be blocked when daily LLM budget is exceeded."""
    # Simulate spending over budget
    event_gate._daily_cost_usd = 999.0  # Way over the $10 default

    allowed, reason = event_gate.should_process(
        OpsEventType.QUALIFIED_LEAD.value,
        entity_id="lead_new",
    )
    assert allowed is False
    assert reason == "budget_exceeded"


def test_rate_limit_blocks_after_daily_cap(event_gate):
    """Module should be blocked after hitting daily execution cap."""
    # executive_digest has a cap of 1 per day
    # Simulate hitting the cap
    event_gate._daily_counts["executive_digest"] = 1

    allowed, reason = event_gate.should_process(
        OpsEventType.DAILY_DIGEST.value,
        entity_id=None,
        module_name="executive_digest",
    )
    assert allowed is False
    assert "rate_limit_hit" in reason


def test_safe_mode_blocks_non_critical_modules(event_gate):
    """When safe mode is active, non-critical modules are blocked."""
    event_gate.activate_safe_mode()

    # usage_product_insights is not in critical_only_modules
    allowed, reason = event_gate.should_process(
        OpsEventType.BATCHED_INSIGHTS.value,
        entity_id=None,
        module_name="usage_product_insights",
    )
    assert allowed is False
    assert reason == "safe_mode_non_critical"


def test_safe_mode_allows_critical_modules(event_gate):
    """When safe mode is active, critical modules are still allowed."""
    event_gate.activate_safe_mode()

    # executive_digest is in critical_only_modules
    allowed, reason = event_gate.should_process(
        OpsEventType.DAILY_DIGEST.value,
        entity_id=None,
        module_name="executive_digest",
    )
    assert allowed is True


def test_ops_flow_disabled_blocks_everything(event_gate, monkeypatch):
    """When OPS_FLOW_ENABLED=false, all events are blocked."""
    from ringsnap_ops_flow import config
    monkeypatch.setattr(config.settings, "ops_flow_enabled", False)

    allowed, reason = event_gate.should_process(
        OpsEventType.QUALIFIED_LEAD.value,
        entity_id="lead_001",
    )
    assert allowed is False
    assert reason == "ops_flow_disabled"


def test_reset_daily_counters_clears_state(event_gate):
    """After reset, counts and costs should be zero."""
    event_gate._daily_counts["sales_triage"] = 50
    event_gate._daily_cost_usd = 5.0
    event_gate.reset_daily_counters()
    assert event_gate.get_daily_counts() == {}
    assert event_gate.get_daily_cost_usd() == 0.0


def test_record_execution_increments_counters(event_gate):
    """record_execution should update module counts and total cost."""
    event_gate.record_execution("sales_triage", cost_usd=0.001)
    event_gate.record_execution("sales_triage", cost_usd=0.002)
    counts = event_gate.get_daily_counts()
    assert counts["sales_triage"] == 2
    assert abs(event_gate.get_daily_cost_usd() - 0.003) < 1e-9
